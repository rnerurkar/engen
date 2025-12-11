"""
Agent-to-Agent (A2A) Communication Library
Provides robust, typed communication between agents in the swarm
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Use relative import since we're in the lib package
from .adk_core import AgentRequest, AgentResponse, TaskStatus

logger = logging.getLogger("A2AClient")


class A2AError(Exception):
    """Base exception for A2A communication errors"""
    pass


class AgentTimeoutError(A2AError):
    """Raised when agent call exceeds timeout"""
    pass


class AgentNotAvailableError(A2AError):
    """Raised when target agent is not reachable"""
    pass


class A2AClient:
    """
    Agent-to-Agent Communication Client
    Handles HTTP communication between agents with retries, timeouts, and error handling
    """
    
    def __init__(
        self,
        agent_name: str,
        default_timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.agent_name = agent_name
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.default_timeout),
            headers={"User-Agent": f"A2AClient/{self.agent_name}"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def call_agent(
        self,
        agent_url: str,
        task: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call another agent and return the result
        
        Args:
            agent_url: Base URL of the target agent
            task: Task name to execute
            payload: Task-specific data
            timeout: Override default timeout
            context: Additional context for the task
            request_id: Request ID for tracing (generated if not provided)
            
        Returns:
            Result dictionary from the agent
            
        Raises:
            AgentTimeoutError: If the call exceeds timeout
            AgentNotAvailableError: If the agent is unreachable
            A2AError: For other communication errors
        """
        timeout = timeout or self.default_timeout
        request_id = request_id or f"{self.agent_name}-{int(datetime.utcnow().timestamp()*1000)}"
        
        # Build the request
        request = AgentRequest(
            task=task,
            payload=payload,
            request_id=request_id,
            sender=self.agent_name,
            timestamp=datetime.utcnow().isoformat(),
            context=context,
            timeout_seconds=timeout
        )
        
        # Ensure we have a session
        should_close = False
        if not self.session:
            self.session = aiohttp.ClientSession()
            should_close = True
        
        try:
            logger.info(f"[{request_id}] Calling agent at {agent_url} for task: {task}")
            
            response_data = await self._call_with_retry(
                agent_url=agent_url,
                request=request,
                timeout=timeout
            )
            
            # Parse response
            agent_response = AgentResponse(**response_data)
            
            if agent_response.status == TaskStatus.COMPLETED:
                logger.info(
                    f"[{request_id}] Agent call successful "
                    f"(took {agent_response.execution_time_ms:.2f}ms)"
                )
                return agent_response.result or {}
            
            elif agent_response.status == TaskStatus.FAILED:
                error_msg = agent_response.error or "Unknown error"
                logger.error(f"[{request_id}] Agent returned failure: {error_msg}")
                raise A2AError(f"Agent task failed: {error_msg}")
            
            elif agent_response.status == TaskStatus.TIMEOUT:
                logger.error(f"[{request_id}] Agent task timed out")
                raise AgentTimeoutError(f"Agent task exceeded timeout of {timeout}s")
            
            else:
                logger.warning(f"[{request_id}] Unexpected status: {agent_response.status}")
                return agent_response.result or {}
                
        finally:
            if should_close and self.session:
                await self.session.close()
                self.session = None
    
    async def _call_with_retry(
        self,
        agent_url: str,
        request: AgentRequest,
        timeout: int
    ) -> Dict[str, Any]:
        """Execute agent call with retry logic"""
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{agent_url}/invoke",
                    json=request.dict(),
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    
                    elif response.status == 503:
                        # Service unavailable, retry
                        logger.warning(
                            f"[{request.request_id}] Agent unavailable (attempt {attempt+1}/{self.max_retries})"
                        )
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        raise AgentNotAvailableError(f"Agent at {agent_url} is unavailable")
                    
                    else:
                        error_text = await response.text()
                        raise A2AError(
                            f"Agent returned status {response.status}: {error_text}"
                        )
            
            except asyncio.TimeoutError as e:
                logger.error(
                    f"[{request.request_id}] Timeout calling agent (attempt {attempt+1}/{self.max_retries})"
                )
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise AgentTimeoutError(f"Agent call timed out after {timeout}s")
            
            except aiohttp.ClientError as e:
                logger.error(
                    f"[{request.request_id}] Client error (attempt {attempt+1}/{self.max_retries}): {e}"
                )
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise AgentNotAvailableError(f"Cannot connect to agent at {agent_url}: {e}")
        
        # If we exhausted retries
        if last_exception:
            raise A2AError(f"Failed after {self.max_retries} attempts: {last_exception}")
        
        raise A2AError("Unexpected error in retry loop")
    
    async def check_health(self, agent_url: str) -> Dict[str, Any]:
        """
        Check if an agent is healthy and available
        
        Returns:
            Health status dictionary
        """
        should_close = False
        if not self.session:
            self.session = aiohttp.ClientSession()
            should_close = True
        
        try:
            async with self.session.get(
                f"{agent_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy", "code": response.status}
        except Exception as e:
            logger.error(f"Health check failed for {agent_url}: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            if should_close and self.session:
                await self.session.close()
                self.session = None
    
    async def get_capabilities(self, agent_url: str) -> Dict[str, Any]:
        """
        Get the capabilities of a target agent
        
        Returns:
            Capabilities dictionary
        """
        should_close = False
        if not self.session:
            self.session = aiohttp.ClientSession()
            should_close = True
        
        try:
            async with self.session.get(
                f"{agent_url}/capabilities",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"Failed to get capabilities from {agent_url}: {e}")
            return {}
        finally:
            if should_close and self.session:
                await self.session.close()
                self.session = None
    
    async def parallel_call(
        self,
        calls: List[Dict[str, Any]],
        fail_fast: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple agent calls in parallel
        
        Args:
            calls: List of call specifications, each containing:
                   {agent_url, task, payload, timeout?, context?}
            fail_fast: If True, cancel remaining calls on first failure
            
        Returns:
            List of results in the same order as calls
        """
        tasks = []
        for call_spec in calls:
            task = self.call_agent(
                agent_url=call_spec["agent_url"],
                task=call_spec["task"],
                payload=call_spec["payload"],
                timeout=call_spec.get("timeout"),
                context=call_spec.get("context")
            )
            tasks.append(task)
        
        if fail_fast:
            # Return on first completion, cancel others on exception
            results = await asyncio.gather(*tasks)
        else:
            # Gather all results, collecting exceptions
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


class A2AClientPool:
    """
    Pool of A2A clients for managing multiple concurrent agent calls
    """
    
    def __init__(self, agent_name: str, pool_size: int = 10):
        self.agent_name = agent_name
        self.pool_size = pool_size
        self.clients: List[A2AClient] = []
        
    async def __aenter__(self):
        """Initialize the client pool"""
        self.clients = [
            A2AClient(self.agent_name)
            for _ in range(self.pool_size)
        ]
        for client in self.clients:
            await client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the client pool"""
        for client in self.clients:
            await client.__aexit__(exc_type, exc_val, exc_tb)
    
    def get_client(self) -> A2AClient:
        """Get a client from the pool (round-robin)"""
        if not self.clients:
            raise RuntimeError("Client pool not initialized. Use 'async with' context manager.")
        # Simple round-robin (could be improved with load balancing)
        client = self.clients[0]
        self.clients.append(self.clients.pop(0))
        return client
