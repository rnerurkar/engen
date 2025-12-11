import msal
import requests
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SharePointClient:
    # Token refresh buffer - refresh 5 minutes before expiry
    TOKEN_REFRESH_BUFFER_SECONDS = 300
    
    def __init__(self, config):
        self.cfg = config
        self.access_token = None
        self.token_expires_at = None
        self._msal_app = msal.ConfidentialClientApplication(
            self.cfg.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{self.cfg.AZURE_TENANT_ID}",
            client_credential=self.cfg.AZURE_CLIENT_SECRET
        )
        self._authenticate()

    def _authenticate(self):
        """Acquires token via Client Credentials Flow"""
        result = self._msal_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" in result:
            self.access_token = result["access_token"]
            # Token typically expires in 1 hour (3600 seconds)
            expires_in = result.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            logger.info(f"Token acquired, expires at {self.token_expires_at.isoformat()}")
        else:
            raise Exception(f"Failed to authenticate with Graph API: {result.get('error_description')}")

    def _ensure_valid_token(self):
        """Check and refresh token if expired or about to expire"""
        if self.token_expires_at is None:
            self._authenticate()
            return
        
        # Refresh if token expires within buffer period
        refresh_threshold = datetime.utcnow() + timedelta(seconds=self.TOKEN_REFRESH_BUFFER_SECONDS)
        if self.token_expires_at <= refresh_threshold:
            logger.info("Token expiring soon, refreshing...")
            self._authenticate()

    def get_headers(self):
        """Get authorization headers with valid token"""
        self._ensure_valid_token()
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def _get_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        """Execute GET request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                
                if response.status_code == 429:
                    # Rate limited - check Retry-After header
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited (429), waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                if response.status_code == 503:
                    # Service unavailable - exponential backoff
                    wait_time = 2 ** attempt
                    logger.warning(f"Service unavailable (503), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request timeout, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed: {e}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Failed after {max_retries} attempts")

    def fetch_pattern_list(self):
        """Fetches metadata from the Pattern Catalog List with pagination"""
        url = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/lists/{self.cfg.SP_LIST_ID}/items?expand=fields"
        patterns = []
        
        while url:
            response = self._get_with_retry(url)
            data = response.json()
            
            for item in data.get('value', []):
                fields = item.get('fields', {})
                # Extract Page URL (assuming 'PatternLink' is a Hyperlink column)
                page_url = fields.get('PatternLink', {}).get('Url')
                
                patterns.append({
                    "id": str(fields.get('PatternID', item['id'])),
                    "title": fields.get('Title'),
                    "maturity": fields.get('MaturityLevel'),
                    "frequency": fields.get('UsageCount', 0),
                    "page_url": page_url,
                    "sharepoint_id": item['id'],  # Needed to fetch page content
                    "content_hash": fields.get('ContentHash')  # For synchronized validation
                })
            
            # Check for next page
            url = data.get('@odata.nextLink')
            if url:
                logging.info(f"Fetching next page of patterns... (total so far: {len(patterns)})")
        
        logging.info(f"Fetched {len(patterns)} patterns total")
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
        resp = self._get_with_retry(query_url)
        data = resp.json()
        
        if not data.get('value'):
            logger.warning(f"Page not found for {filename}")
            return ""

        # Extract the CanvasContent1 which contains the HTML structure of the page
        raw_html = data['value'][0]['fields'].get('CanvasContent1', '')
        return raw_html

    def download_image(self, image_source_url):
        """Downloads image bytes from SharePoint Drive"""
        # image_source_url is usually relative: /sites/mysite/SiteAssets/img.png
        # We need to construct the Graph download URL
        drive_path = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/drive/root:{image_source_url}:/content"
        try:
            response = self._get_with_retry(drive_path)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"Failed to download image {image_source_url}: {e}")
        return None