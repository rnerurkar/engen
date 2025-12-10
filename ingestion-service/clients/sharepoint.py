import msal
import requests
import logging

class SharePointClient:
    def __init__(self, config):
        self.cfg = config
        self.access_token = None
        self._authenticate()

    def _authenticate(self):
        """Acquires token via Client Credentials Flow"""
        app = msal.ConfidentialClientApplication(
            self.cfg.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{self.cfg.AZURE_TENANT_ID}",
            client_credential=self.cfg.AZURE_CLIENT_SECRET
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            self.access_token = result["access_token"]
        else:
            raise Exception(f"Failed to authenticate with Graph API: {result.get('error_description')}")

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def fetch_pattern_list(self):
        """Fetches metadata from the Pattern Catalog List"""
        url = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/lists/{self.cfg.SP_LIST_ID}/items?expand=fields"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        
        patterns = []
        for item in response.json().get('value', []):
            fields = item.get('fields', {})
            # Extract Page URL (assuming 'PatternLink' is a Hyperlink column)
            page_url = fields.get('PatternLink', {}).get('Url')
            
            patterns.append({
                "id": str(fields.get('PatternID', item['id'])),
                "title": fields.get('Title'),
                "maturity": fields.get('MaturityLevel'),
                "frequency": fields.get('UsageCount', 0),
                "page_url": page_url,
                "sharepoint_id": item['id'] # Needed to fetch page content
            })
        return patterns

    def fetch_page_html(self, page_url):
        """
        Fetches the CanvasContent1 (WebParts) from a Site Page.
        We parse the Page URL to find the Page ID (or query by URL).
        """
        # Logic to resolve Page ID from URL is simplified here. 
        # In prod, query the Site Pages library by FileLeafRef.
        filename = page_url.split('/')[-1]
        
        query_url = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/lists/SitePages/items?filter=fields/FileLeafRef eq '{filename}'&expand=fields"
        resp = requests.get(query_url, headers=self.get_headers())
        data = resp.json()
        
        if not data.get('value'):
            logging.warning(f"Page not found for {filename}")
            return ""

        # Extract the CanvasContent1 which contains the HTML structure of the page
        raw_html = data['value'][0]['fields'].get('CanvasContent1', '')
        return raw_html

    def download_image(self, image_source_url):
        """Downloads image bytes from SharePoint Drive"""
        # image_source_url is usually relative: /sites/mysite/SiteAssets/img.png
        # We need to construct the Graph download URL
        drive_path = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/drive/root:{image_source_url}:/content"
        response = requests.get(drive_path, headers=self.get_headers())
        if response.status_code == 200:
            return response.content
        return None