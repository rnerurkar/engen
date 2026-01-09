"""
Transaction Manager for Atomic Multi-Stream Ingestion
Implements two-phase commit pattern for Streams A, B, and C
"""

import asyncio
import logging
import shutil
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class StreamResult:
    """Result from a stream processing operation"""
    stream_name: str
    status: str  # 'prepared', 'committed', 'failed', 'rolled_back'
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TransactionState:
    """Tracks the state of a pattern ingestion transaction"""
    pattern_id: str
    pattern_title: str
    staging_dir: Path
    stream_results: Dict[str, StreamResult] = field(default_factory=dict)
    phase: str = 'init'  # 'init', 'preparing', 'prepared', 'committing', 'committed', 'failed', 'rolled_back'
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize transaction state for logging/recovery"""
        return {
            'pattern_id': self.pattern_id,
            'pattern_title': self.pattern_title,
            'phase': self.phase,
            'stream_results': {
                name: {
                    'status': result.status,
                    'error': result.error,
                    'timestamp': result.timestamp
                }
                for name, result in self.stream_results.items()
            },
            'start_time': self.start_time,
            'error': self.error
        }


class IngestionTransaction:
    """
    Manages atomic ingestion transaction across three streams.
    
    SYSTEM DESIGN NOTE: Two-Phase Commit (2PC) Pattern
    --------------------------------------------------
    We are ingesting data into 3 disparate systems (Discovery Engine, Vector Search, Firestore).
    Since these systems do not share a transaction log, we must implement a distributed transaction manually.
    
    Phase 1: Prepare (Parallel)
    - Validate the data for all streams.
    - Transform data into the required formats.
    - Save prepared data to a temporary staging area.
    - DO NOT write to production yet.
    - If ANY stream fails here, we abort the whole process safely.
    
    Phase 2: Commit (Sequential)
    - Take the staged data and write to production.
    - If ANY stream fails here, we must ROLLBACK the already committed streams 
      to ensure we don't end up with partial data (e.g., text exists but images are missing).
    """
    
    def __init__(self, pattern_id: str, pattern_title: str, staging_base: str = "/tmp/engen_staging"):
        self.state = TransactionState(
            pattern_id=pattern_id,
            pattern_title=pattern_title,
            staging_dir=Path(staging_base) / pattern_id
        )
        
    def _ensure_staging_dir(self):
        """Create staging directory for this transaction"""
        self.state.staging_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Staging directory: {self.state.staging_dir}")
    
    def _cleanup_staging(self):
        """
        Clean up the temporary files used during the 'Prepare' phase.
        This is called after a successful Commit or after a Rollback.
        """
        try:
            if self.state.staging_dir.exists():
                shutil.rmtree(self.state.staging_dir)
                logger.debug(f"Cleaned up staging directory: {self.state.staging_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup staging directory: {e}")
    
    async def prepare(
        self,
        processors: Dict[str, Any],
        metadata: Dict[str, Any],
        html_content: str
    ) -> bool:
        """
        Phase 1: Prepare all streams in parallel without committing to production storage.
        
        SYSTEM DESIGN NOTE: Parallel Execution
        We use `asyncio.gather` here because the work for Stream A, B, and C is independent 
        at this stage. They can all process the HTML concurrently, improving performance.
        
        Returns:
            True if all streams prepared successfully, False otherwise
        """
        self.state.phase = 'preparing'
        self._ensure_staging_dir()
        
        logger.info(f"[{self.state.pattern_id}] Phase 1: Preparing streams A, B, C in parallel...")
        
        try:
            # Execute all three streams in parallel
            # We catch exceptions so one failure doesn't crash the loop immediately,
            # allowing us to log specific errors for each stream.
            results = await asyncio.gather(
                self._prepare_stream(processors['A'], 'A', metadata, html_content),
                self._prepare_stream(processors['B'], 'B', metadata, html_content),
                self._prepare_stream(processors['C'], 'C', metadata, html_content),
                return_exceptions=True
            )
            
            # Check if all succeeded
            failures = []
            for i, result in enumerate(results):
                stream_name = ['A', 'B', 'C'][i]
                if isinstance(result, Exception):
                    error_msg = str(result)
                    logger.error(f"[{self.state.pattern_id}] Stream {stream_name} preparation failed: {error_msg}")
                    self.state.stream_results[stream_name] = StreamResult(
                        stream_name=stream_name,
                        status='failed',
                        error=error_msg
                    )
                    failures.append(stream_name)
                elif not result:
                    error_msg = f"Stream {stream_name} returned False"
                    logger.error(f"[{self.state.pattern_id}] {error_msg}")
                    self.state.stream_results[stream_name] = StreamResult(
                        stream_name=stream_name,
                        status='failed',
                        error=error_msg
                    )
                    failures.append(stream_name)
                else:
                    logger.info(f"[{self.state.pattern_id}] Stream {stream_name} prepared successfully")
            
            # ATOMICITY CHECK:
            # If even one stream failed to prepare, the entire transaction is marked as failed.
            # We do NOT proceed to Phase 2 (Commit).
            if failures:
                self.state.phase = 'failed'
                self.state.error = f"Streams {', '.join(failures)} failed during preparation"
                self._cleanup_staging()
                logger.error(f"[{self.state.pattern_id}] Preparation failed: {self.state.error}")
                return False
            
            self.state.phase = 'prepared'
            logger.info(f"[{self.state.pattern_id}] All streams prepared successfully")
            return True
            
        except Exception as e:
            self.state.phase = 'failed'
            self.state.error = f"Unexpected error during preparation: {str(e)}"
            logger.error(f"[{self.state.pattern_id}] {self.state.error}", exc_info=True)
            self._cleanup_staging()
            return False
    
    async def _prepare_stream(
        self,
        processor: Any,
        stream_name: str,
        metadata: Dict[str, Any],
        html_content: str
    ) -> bool:
        """
        Prepare a single stream (staging only, no production writes)
        
        Returns:
            True if preparation succeeded
        """
        try:
            result = await processor.prepare(
                metadata=metadata,
                html_content=html_content,
                staging_dir=self.state.staging_dir
            )
            
            self.state.stream_results[stream_name] = StreamResult(
                stream_name=stream_name,
                status='prepared',
                data=result
            )
            return True
            
        except Exception as e:
            logger.error(f"Stream {stream_name} preparation error: {e}", exc_info=True)
            raise
    
    async def commit(self, processors: Dict[str, Any]) -> bool:
        """
        Phase 2: Commit all prepared streams to production storage.
        
        SYSTEM DESIGN NOTE: Sequential Commit
        Unlike the 'Prepare' phase, we commit sequentially (A -> B -> C).
        Why?
        1. Fault Isolation: If A fails, we don't even try B or C. We just fail.
        2. Rollback Simplicity: If C fails, we know exactly what to rollback (A and B).
           If we did this in parallel and 2 out of 3 failed, calculating the compensation logic is harder.
        
        Returns:
            True if all commits succeeded, False otherwise (triggers rollback)
        """
        if self.state.phase != 'prepared':
            raise RuntimeError(f"Cannot commit: transaction in phase '{self.state.phase}'")
        
        self.state.phase = 'committing'
        logger.info(f"[{self.state.pattern_id}] Phase 2: Committing streams A, B, C...")
        
        # Commit in sequence to handle failures with rollback
        # Order: A -> B -> C (can rollback in reverse if needed)
        committed_streams = []
        
        try:
            # Commit Stream A (Semantic)
            if await self._commit_stream(processors['A'], 'A'):
                committed_streams.append('A')
                logger.info(f"[{self.state.pattern_id}] Stream A committed")
            else:
                raise Exception("Stream A commit failed")
            
            # Commit Stream B (Visual)
            if await self._commit_stream(processors['B'], 'B'):
                committed_streams.append('B')
                logger.info(f"[{self.state.pattern_id}] Stream B committed")
            else:
                raise Exception("Stream B commit failed")
            
            # Commit Stream C (Content)
            if await self._commit_stream(processors['C'], 'C'):
                committed_streams.append('C')
                logger.info(f"[{self.state.pattern_id}] Stream C committed")
            else:
                raise Exception("Stream C commit failed")
            
            # All commits succeeded
            self.state.phase = 'committed'
            self._cleanup_staging()
            logger.info(f"[{self.state.pattern_id}] ✓ Transaction committed successfully")
            return True
            
        except Exception as e:
            # Commit failed - rollback all committed streams
            self.state.error = f"Commit failed: {str(e)}"
            logger.error(f"[{self.state.pattern_id}] Commit failed, rolling back...", exc_info=True)
            
            # TRIGGER ROLLBACK:
            # This is the "Compensating Transaction" logic.
            # We undo whatever we successfully did before the error occurred.
            await self.rollback(processors, committed_streams)
            return False
    
    async def _commit_stream(
        self,
        processor: Any,
        stream_name: str
    ) -> bool:
        """
        Commit a single stream to production storage
        
        Returns:
            True if commit succeeded
        """
        try:
            result_data = self.state.stream_results[stream_name].data
            await processor.commit(result_data)
            
            self.state.stream_results[stream_name].status = 'committed'
            return True
            
        except Exception as e:
            logger.error(f"Stream {stream_name} commit error: {e}", exc_info=True)
            self.state.stream_results[stream_name].status = 'failed'
            self.state.stream_results[stream_name].error = str(e)
            raise
    
    async def rollback(
        self,
        processors: Dict[str, Any],
        committed_streams: Optional[List[str]] = None
    ) -> None:
        """
        Rollback any committed streams (in reverse order).
        
        SYSTEM DESIGN NOTE: Compensation Logic
        This effectively "undoes" the Commit phase.
        It uses a LIFO (Last-In-First-Out) stack approach.
        If we committed A -> B, and then failed at C:
        1. We are given committed_streams=['A', 'B']
        2. We reverse it: ['B', 'A']
        3. We call processor.rollback for B.
        4. We call processor.rollback for A.
        
        This ensures we unwind the system state cleanly.
        """
        self.state.phase = 'rolling_back'
        
        if committed_streams is None:
            # Rollback all streams that were committed
            committed_streams = [
                name for name, result in self.state.stream_results.items()
                if result.status == 'committed'
            ]
        
        logger.warning(f"[{self.state.pattern_id}] Rolling back streams: {committed_streams}")
        
        # Rollback in reverse order (C -> B -> A)
        for stream_name in reversed(committed_streams):
            try:
                processor = processors[stream_name]
                result_data = self.state.stream_results[stream_name].data
                
                await processor.rollback(result_data)
                self.state.stream_results[stream_name].status = 'rolled_back'
                logger.info(f"[{self.state.pattern_id}] Stream {stream_name} rolled back")
                
            except Exception as e:
                logger.error(f"[{self.state.pattern_id}] Failed to rollback stream {stream_name}: {e}")
                # Continue with other rollbacks even if one fails. 
                # In a real production system, this catastrophic failure (rollback failed) 
                # might raise a critical alert to a human operator or Dead Letter Queue.
        
        self.state.phase = 'rolled_back'
        self._cleanup_staging()
        logger.warning(f"[{self.state.pattern_id}] Transaction rolled back")
    
    def save_state(self, checkpoint_dir: str = "/tmp/engen_checkpoints"):
        """Save transaction state to disk for recovery"""
        try:
            checkpoint_path = Path(checkpoint_dir)
            checkpoint_path.mkdir(parents=True, exist_ok=True)
            
            state_file = checkpoint_path / f"{self.state.pattern_id}.json"
            with open(state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
            
            logger.debug(f"Saved transaction state: {state_file}")
        except Exception as e:
            logger.warning(f"Failed to save transaction state: {e}")


class TransactionCoordinator:
    """
    Coordinates multiple ingestion transactions with progress tracking
    """
    
    def __init__(self, checkpoint_dir: str = "/tmp/engen_checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self.completed_patterns: set = set()
        self._load_completed()
    
    def _load_completed(self):
        """Load list of already-completed patterns for idempotency"""
        checkpoint_path = Path(self.checkpoint_dir)
        if not checkpoint_path.exists():
            return
        
        for state_file in checkpoint_path.glob("*.json"):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    if state.get('phase') == 'committed':
                        self.completed_patterns.add(state['pattern_id'])
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {state_file}: {e}")
        
        if self.completed_patterns:
            logger.info(f"Loaded {len(self.completed_patterns)} completed patterns from checkpoints")
    
    def is_completed(self, pattern_id: str) -> bool:
        """Check if pattern was already successfully ingested"""
        return pattern_id in self.completed_patterns
    
    def mark_completed(self, pattern_id: str):
        """Mark pattern as completed"""
        self.completed_patterns.add(pattern_id)
    
    async def execute_transaction(
        self,
        transaction: IngestionTransaction,
        processors: Dict[str, Any],
        metadata: Dict[str, Any],
        html_content: str
    ) -> bool:
        """
        Execute a full two-phase commit transaction
        
        Returns:
            True if transaction succeeded, False otherwise
        """
        try:
            # Phase 1: Prepare (parallel)
            if not await transaction.prepare(processors, metadata, html_content):
                logger.error(f"Transaction preparation failed for {transaction.state.pattern_id}")
                return False
            
            # Save state after preparation
            transaction.save_state(self.checkpoint_dir)
            
            # Phase 2: Commit (sequential with rollback)
            if not await transaction.commit(processors):
                logger.error(f"Transaction commit failed for {transaction.state.pattern_id}")
                return False
            
            # Mark as completed
            self.mark_completed(transaction.state.pattern_id)
            transaction.save_state(self.checkpoint_dir)
            
            return True
            
        except Exception as e:
            logger.error(f"Transaction execution error: {e}", exc_info=True)
            return False
