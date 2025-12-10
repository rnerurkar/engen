from google.cloud import firestore
from bs4 import BeautifulSoup
import markdownify

class StreamCProcessor:
    def __init__(self, config):
        self.db = firestore.Client()
        self.collection = config.FIRESTORE_COLLECTION

    def process(self, metadata, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        batch = self.db.batch()
        
        # 1. Logic to split by H2 headers
        # This iterates the DOM to group content under headers
        current_section = "Overview"
        buffer = []
        
        # Simple parser loop
        for element in soup.recursiveChildGenerator():
            if element.name == 'h2':
                # Save previous section
                self._add_to_batch(batch, metadata['id'], current_section, buffer)
                # Start new section
                current_section = element.get_text().strip()
                buffer = []
            elif element.name in ['p', 'table', 'ul', 'div']:
                buffer.append(str(element))
                
        # Save last section
        self._add_to_batch(batch, metadata['id'], current_section, buffer)
        
        # 2. Commit to Firestore
        batch.commit()

    def _add_to_batch(self, batch, pat_id, sec_name, html_list):
        if not html_list: return
        full_html = "".join(html_list)
        
        # Convert Tables to Markdown
        md_text = markdownify.markdownify(full_html).strip()
        
        if md_text:
            ref = self.db.collection(self.collection).document(pat_id).collection('sections').document(sec_name)
            batch.set(ref, {
                "section_name": sec_name,
                "plain_text": md_text,
                "pattern_id": pat_id
            })