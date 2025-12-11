from google.cloud import firestore
from bs4 import BeautifulSoup
import markdownify
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StreamCProcessor:
    """Stream C: Content Atomization (Firestore)"""
    
    def __init__(self, config):
        self.config = config
        self.db = firestore.Client()
        self.collection = config.FIRESTORE_COLLECTION

    async def prepare(self, metadata: Dict[str, Any], html_content: str, staging_dir: Path) -> Dict[str, Any]:
        """
        Phase 1: Parse and prepare content sections (not written to Firestore yet)
        
        Returns:
            Dict containing prepared sections
        """
        try:
            if not html_content or len(html_content) < 100:
                raise ValueError("Insufficient HTML content")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            sections = []
            
            # Parse sections by H2 headers
            current_section = "Overview"
            buffer = []
            
            logger.debug(f"[Stream C] Parsing HTML structure...")
            
            for element in soup.recursiveChildGenerator():
                if hasattr(element, 'name'):
                    if element.name == 'h2':
                        # Save previous section
                        if buffer:
                            section_data = self._create_section_data(
                                metadata['id'],
                                current_section,
                                buffer
                            )
                            if section_data:
                                sections.append(section_data)
                        
                        # Start new section
                        current_section = element.get_text().strip()
                        if not current_section:
                            current_section = f"Section_{len(sections) + 1}"
                        buffer = []
                        
                    elif element.name in ['p', 'table', 'ul', 'ol', 'div'] and element.string:
                        buffer.append(str(element))
            
            # Save last section
            if buffer:
                section_data = self._create_section_data(
                    metadata['id'],
                    current_section,
                    buffer
                )
                if section_data:
                    sections.append(section_data)
            
            # Validate we extracted sections
            if not sections:
                # Try alternative parsing strategy - split by any heading
                logger.warning(f"[Stream C] No H2 sections found, trying alternative parsing")
                sections = self._parse_by_any_heading(soup, metadata['id'])
            
            if not sections:
                raise ValueError("No content sections could be extracted from HTML")
            
            # Note: Chunking handled in commit() for patterns with >500 sections
            if len(sections) > 2000:
                logger.warning(f"[Stream C] Large document with {len(sections)} sections - will process in chunks")
            
            logger.info(f"[Stream C] Prepared {len(sections)} sections")
            
            # Save to staging
            staging_file = staging_dir / "stream_c_sections.json"
            with open(staging_file, 'w') as f:
                json.dump({
                    'sections': sections,
                    'pattern_id': metadata['id'],
                    'section_count': len(sections)
                }, f, indent=2)
            
            return {
                'sections': sections,
                'pattern_id': metadata['id'],
                'staging_file': str(staging_file)
            }
            
        except Exception as e:
            logger.error(f"[Stream C] Preparation failed: {e}", exc_info=True)
            raise

    def _create_section_data(self, pattern_id: str, section_name: str, html_list: List[str]) -> Dict[str, Any]:
        """Create section data from HTML elements"""
        if not html_list:
            return None
        
        full_html = "".join(html_list)
        
        # Convert to Markdown
        try:
            md_text = markdownify.markdownify(full_html, heading_style="ATX").strip()
        except Exception as e:
            logger.warning(f"[Stream C] Markdown conversion failed for {section_name}: {e}")
            # Fallback to plain text
            soup = BeautifulSoup(full_html, 'html.parser')
            md_text = soup.get_text(separator="\n").strip()
        
        if not md_text or len(md_text) < 10:
            logger.debug(f"[Stream C] Section '{section_name}' too short, skipping")
            return None
        
        # Sanitize section name for Firestore document ID
        safe_section_name = section_name.replace('/', '_').replace('\\', '_')[:100]
        
        return {
            'section_name': section_name,
            'safe_section_name': safe_section_name,
            'plain_text': md_text,
            'pattern_id': pattern_id,
            'char_count': len(md_text),
            'word_count': len(md_text.split())
        }

    def _parse_by_any_heading(self, soup: BeautifulSoup, pattern_id: str) -> List[Dict[str, Any]]:
        """Alternative parsing strategy using any heading level"""
        sections = []
        current_section = "Overview"
        buffer = []
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'table', 'ul', 'ol', 'div']):
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                if buffer:
                    section_data = self._create_section_data(pattern_id, current_section, buffer)
                    if section_data:
                        sections.append(section_data)
                current_section = element.get_text().strip() or f"Section_{len(sections) + 1}"
                buffer = []
            else:
                if element.string or element.get_text(strip=True):
                    buffer.append(str(element))
        
        if buffer:
            section_data = self._create_section_data(pattern_id, current_section, buffer)
            if section_data:
                sections.append(section_data)
        
        return sections

    async def commit(self, prepared_data: Dict[str, Any]) -> None:
        """
        Phase 2: Write sections to Firestore with chunking and retry for large documents
        """
        try:
            sections = prepared_data['sections']
            pattern_id = prepared_data['pattern_id']
            
            if not sections:
                logger.warning(f"[Stream C] No sections to commit for pattern {pattern_id}")
                return
            
            logger.info(f"[Stream C] Committing {len(sections)} sections to Firestore...")
            
            # Chunk into batches of 500 (Firestore batch limit)
            chunk_size = 500
            total_chunks = (len(sections) + chunk_size - 1) // chunk_size
            
            for chunk_idx in range(0, len(sections), chunk_size):
                chunk = sections[chunk_idx:chunk_idx + chunk_size]
                
                # Retry logic for transient Firestore failures
                await self._commit_chunk_with_retry(
                    chunk, 
                    pattern_id, 
                    chunk_num=(chunk_idx // chunk_size) + 1,
                    total_chunks=total_chunks
                )
            
            logger.info(f"[Stream C] ✓ Committed all {len(sections)} sections for pattern {pattern_id}")
            
        except Exception as e:
            logger.error(f"[Stream C] Commit failed: {e}", exc_info=True)
            raise

    async def _commit_chunk_with_retry(
        self, 
        chunk: List[Dict[str, Any]], 
        pattern_id: str, 
        chunk_num: int,
        total_chunks: int,
        max_retries: int = 3
    ) -> None:
        """Commit a chunk of sections with exponential backoff retry"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                batch = self.db.batch()
                
                for section_data in chunk:
                    section_name = section_data['safe_section_name']
                    
                    ref = (self.db.collection(self.collection)
                          .document(pattern_id)
                          .collection('sections')
                          .document(section_name))
                    
                    batch.set(ref, {
                        'section_name': section_data['section_name'],
                        'plain_text': section_data['plain_text'],
                        'pattern_id': pattern_id,
                        'char_count': section_data['char_count'],
                        'word_count': section_data['word_count']
                    })
                
                # Commit this chunk
                batch.commit()
                
                logger.info(f"[Stream C] Committed chunk {chunk_num}/{total_chunks} ({len(chunk)} sections)")
                return
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"[Stream C] Chunk {chunk_num} commit failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Stream C] Chunk {chunk_num} commit failed after {max_retries} attempts")
                    raise

    async def rollback(self, prepared_data: Dict[str, Any]) -> None:
        """
        Rollback: Delete all sections for this pattern from Firestore
        """
        try:
            pattern_id = prepared_data['pattern_id']
            
            logger.warning(f"[Stream C] Rolling back pattern {pattern_id}...")
            
            # Delete all sections for this pattern
            sections_ref = (self.db.collection(self.collection)
                           .document(pattern_id)
                           .collection('sections'))
            
            # Get all section documents
            docs = sections_ref.stream()
            deleted_count = 0
            
            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Firestore batch limit is 500
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining deletions
            if deleted_count % 500 != 0:
                batch.commit()
            
            # Delete the pattern document itself
            try:
                self.db.collection(self.collection).document(pattern_id).delete()
            except Exception:
                pass  # Document might not exist
            
            logger.info(f"[Stream C] ✓ Deleted {deleted_count} sections (rolled back)")
            
        except Exception as e:
            logger.error(f"[Stream C] Rollback failed: {e}", exc_info=True)
            # Don't raise - best effort rollback