from vertexai.generative_models import GenerativeModel
from google.cloud import discoveryengine_v1 as discoveryengine
import json
from bs4 import BeautifulSoup

class StreamAProcessor:
    def __init__(self, config):
        self.llm = GenerativeModel("gemini-1.5-pro")
        self.client = discoveryengine.DocumentServiceClient()
        self.parent = f"projects/{config.PROJECT_ID}/locations/global/collections/default_collection/dataStores/{config.SEARCH_DATA_STORE_ID}/branches/default_branch"

    def process(self, metadata, html_content):
        # 1. Clean HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        text_dossier = soup.get_text(separator="\n")[:30000] # Context limit

        # 2. Summarize using LLM
        prompt = f"""
        Summarize this architecture pattern into a dense technical abstract (300 words).
        Include: Core Problem, Solution Logic, Key Technologies, and Trade-offs.
        TEXT: {text_dossier}
        """
        summary = self.llm.generate_content(prompt).text

        # 3. Create Document
        doc = discoveryengine.Document(
            id=f"desc_{metadata['id']}",
            json_data=json.dumps({
                "title": metadata['title'],
                "content": summary, # Semantic Anchor
                "maturity": metadata['maturity'],
                "frequency": metadata['frequency'],
                "url": metadata['page_url'],
                "type": "pattern_summary"
            })
        )
        
        # 4. Ingest
        req = discoveryengine.ImportDocumentsRequest(
            parent=self.parent,
            inline_source=discoveryengine.ImportDocumentsRequest.InlineSource(documents=[doc]),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
        )
        operation = self.client.import_documents(request=req)
        operation.result()
        return summary