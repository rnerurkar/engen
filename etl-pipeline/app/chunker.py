import re
import uuid
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SemanticChunker:
    def __init__(self):
        # Regex to split by H1 or H2 headers (## Header)
        self.header_regex = r'(^#{1,2}\s.*$)'

    def chunk_and_join(self, markdown_text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Splits markdown by headers and injects master metadata into every chunk.
        Returns a list of JSON objects ready for Vertex AI ingestion.
        """
        chunks = []
        # Split the text, keeping the delimiters (headers)
        parts = re.split(self.header_regex, markdown_text, flags=re.MULTILINE)
        
        current_header = "Introduction/General"
        current_content = ""

        # Iterate through parts. re.split with capturing groups returns [text, delimiter, text, delimiter...]
        for part in parts:
            part = part.strip()
            if not part: continue

            if re.match(self.header_regex, part):
                # If we hit a new header, save previous accumulated content if it exists
                if current_content:
                    chunks.append(self._create_chunk_payload(current_header, current_content, metadata))
                # Update current header and reset content
                current_header = part.lstrip('#').strip()
                current_content = ""
            else:
                # Accumulate text content under the current header
                current_content += "\n" + part

        # Add the final section lying around after the loop finishes
        if current_content:
             chunks.append(self._create_chunk_payload(current_header, current_content, metadata))

        logger.info(f"Split document into {len(chunks)} semantic chunks.")
        return chunks

    def _create_chunk_payload(self, header: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Creates the final JSON structure for Vertex AI Search."""
        # Combine metadata + current section context for embedding
        rich_context = (
            f"Metadata Context:\n"
            f"- Pattern Name: {metadata.get('PatternName')}\n"
            f"- Status: {metadata.get('LifecycleState')}\n"
            f"- Integration: {metadata.get('SourcePlatform')} to {metadata.get('DestinationPlatform')}\n"
            f"Section Context: {header}\n"
            f"--- Content ---\n{content}"
        )

        # Structure Data: Must match your Vertex AI Search schema requirements.
        # We use 'content' for the unstructured text and 'structData' for filterable fields.
        payload = {
            "id": str(uuid.uuid4()),
            "jsonData": JSON.dumps({
                "content": rich_context,
                # structData fields must be defined in your Data Store schema if you want to filter/facet on them
                "structData": {
                    "source_url": metadata.get('PatternDocumentationURL'),
                    "pattern_name": metadata.get('PatternName'),
                    "lifecycle_state": metadata.get('LifecycleState'),
                    "section_header": header,
                    "governance_date": metadata.get('PatternGovernanceDate')
                }
             })
        }
        return payload
import json as JSON