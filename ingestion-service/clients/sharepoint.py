"""
SharePoint Client Module
------------------------
This module handles all interactions with Microsoft SharePoint Online via the MS Graph API.
It implements the "Adapter Pattern" to translate our domain-specific requests (fetch patterns, get html)
into complex MS Graph API HTTP calls.

Key Responsibilities:
1. Authentication: Manages OAuth2 tokens using MSAL (Client Credentials Flow).
2. Reliability: Implements retry logic with exponential backoff for network resilience.
3. Data Abstraction: Hides the complexity of OData queries and pagination.
"""

import msal
import requests
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SharePointClient:
    """
    A robust client for the Microsoft Graph API tailored for SharePoint operations.
    
    SYSTEM DESIGN NOTE: Token Management
    ------------------------------------
    We use the 'Client Credentials Flow' which is suitable for daemons/background services.
    Instead of logging in as a user, we log in as the Application itself using a Client Secret.
    The client proactively refreshes tokens before they expire to prevent 401 errors during long batch jobs.
    """
    
    # Token refresh buffer - refresh 5 minutes before expiry to be safe
    TOKEN_REFRESH_BUFFER_SECONDS = 300
    
    def __init__(self, config):
        self.cfg = config
        self.access_token = None
        self.token_expires_at = None
        
        # Initialize MSAL Confidential Client
        # This is the standard library for MS identity platform
        self._msal_app = msal.ConfidentialClientApplication(
            self.cfg.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{self.cfg.AZURE_TENANT_ID}",
            client_credential=self.cfg.AZURE_CLIENT_SECRET
        )
        # Initial login
        self._authenticate()

    def _authenticate(self):
        """
        Acquires a new OAuth2 access token from Azure AD.
        
        This uses the 'https://graph.microsoft.com/.default' scope which grants all 
        permissions assigned to the application in the Azure Portal.
        """
        result = self._msal_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            
            # Token typically expires in 1 hour (3600 seconds)
            # We calculate the absolute expiry time to check against later
            expires_in = result.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info(f"Token acquired, expires at {self.token_expires_at.isoformat()}")
        else:
            # Critical failure: If we can't auth, the service cannot function.
            raise Exception(f"Failed to authenticate with Graph API: {result.get('error_description')}")

    def _ensure_valid_token(self):
        """
        Checks if the current token is about to expire and refreshes it if needed.
        
        Why this is important?
        Long-running ingestion jobs might take > 1 hour. This check allows the system 
        to run indefinitely without authentication failures.
        """
        if self.token_expires_at is None:
            self._authenticate()
            return
        
        # Calculate if we are inside the unsafe buffer period
        refresh_threshold = datetime.utcnow() + timedelta(seconds=self.TOKEN_REFRESH_BUFFER_SECONDS)
        
        if self.token_expires_at <= refresh_threshold:
            logger.info("Token expiring soon, refreshing...")
            self._authenticate()

    def get_headers(self):
        """Helper to construct Authorization header, ensuring token is fresh first."""
        self._ensure_valid_token()
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def _get_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        """
        Executes a GET request with built-in resilience.
        
        SYSTEM DESIGN NOTE: Error Handling Strategy
        -------------------------------------------
        - 429 (Too Many Requests): Respects the 'Retry-After' header from Microsoft.
        - 503 (Service Unavailable): Uses exponential backoff (2s, 4s, 8s).
        - Timeout: Catches and retries.
        """
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                
                # Handle Rate Limiting (Throttling)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited (429), waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                # Handle Transient Server Errors
                if response.status_code == 503:
                    wait_time = 2 ** attempt # Exponential backoff
                    logger.warning(f"Service unavailable (503), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Raise exception for 4xx/5xx errors so we catch them below
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
                # Catch-all for other network errors
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed: {e}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Failed after {max_retries} attempts")

    def fetch_pattern_list(self):
        """
        Retrieves the catalog of patterns from a SharePoint List.
        
        Concepts:
        - OData Query: We use `?expand=fields` because custom columns in SharePoint are often
          nested inside a 'fields' object in the JSON response.
        - Pagination: The Graph API default page size is usually small (e.g., 20 items).
          We must manually follow the `@odata.nextLink` to get the full dataset.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/lists/{self.cfg.SP_LIST_ID}/items?expand=fields"
        patterns = []
        
        logging.info("Starting pattern catalog fetch...")
        
        while url:
            # Make the request using our resilient getter
            response = self._get_with_retry(url)
            data = response.json()
            
            for item in data.get('value', []):
                fields = item.get('fields', {})
                
                # Robust extraction of URL from Hyperlink column type
                page_url = fields.get('PatternLink', {}).get('Url')
                
                # Map SharePoint list columns to our domain model
                patterns.append({
                    "id": str(fields.get('PatternID', item['id'])), # Business Key
                    "title": fields.get('Title'),
                    "maturity": fields.get('MaturityLevel'),
                    "frequency": fields.get('UsageCount', 0),
                    "page_url": page_url,
                    "sharepoint_id": item['id'],        # System Key (needed for fetching content)
                    "status": fields.get('Status', 'Active').lower(),
                    "owner": fields.get('OwnerGroup', 'Architecture'),
                    "category": fields.get('PatternCategory', 'General'),
                    "content_hash": fields.get('ContentHash') # For idempotency checks
                })
            
            # Check if there are more pages of results
            url = data.get('@odata.nextLink')
            if url:
                logging.info(f"Fetching next page of patterns... (total so far: {len(patterns)})")
        
        logging.info(f"Fetched {len(patterns)} patterns total")
        return patterns

    def fetch_page_html(self, page_url):
        """
        Retrieves the actual HTML content of a SharePoint "Modern Page".
        
        Technical Detail:
        - SharePoint pages are files stored in the "SitePages" library.
        - The actual HTML content (text typed by users) is stored in a hidden field called `CanvasContent1`.
        - We query by filename (`FileLeafRef`) to find the list item, then read that field.
        """
        # 1. Parse filename from URL (e.g. "https://.../SitePages/MyPattern.aspx" -> "MyPattern.aspx")
        if not page_url:
            return ""
        filename = page_url.split('/')[-1]
        
        library = getattr(self.cfg, 'SP_PAGES_LIBRARY', 'SitePages')
        
        # 2. OData Filter Query: Find the file where name equals our filename
        query_url = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/lists/{library}/items?filter=fields/FileLeafRef eq '{filename}'&expand=fields"
        
        resp = self._get_with_retry(query_url)
        data = resp.json()
        
        if not data.get('value'):
            logger.warning(f"Page not found for {filename}")
            return ""

        # 3. Extract the CanvasContent1 which contains the HTML structure of the page
        raw_html = data['value'][0]['fields'].get('CanvasContent1', '')
        return raw_html

    def download_image(self, image_source_url):
        """
        Downloads a binary image file from SharePoint Drive.
        """
        # image_source_url is usually relative: /sites/mysite/SiteAssets/img.png
        # We need to construct the Graph download URL pointing to the 'content' stream
        # Syntax: .../drive/root:{path}:/content
        
        drive_path = f"https://graph.microsoft.com/v1.0/sites/{self.cfg.SP_SITE_ID}/drive/root:{image_source_url}:/content"
        try:
            response = self._get_with_retry(drive_path)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"Failed to download image {image_source_url}: {e}")
        return None
