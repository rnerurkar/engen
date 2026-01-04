import os
import logging
import requests
import msal
import re
from urllib.parse import unquote
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MSGraphClient:
    def __init__(self):
        self.client_id = os.environ.get("SP_CLIENT_ID")
        self.client_secret = os.environ.get("SP_CLIENT_SECRET")
        self.tenant_id = os.environ.get("SP_TENANT_ID")
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
             raise ValueError("Missing required environment variables for SharePoint Auth.")

        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.access_token = None
        # Regex to parse standard SharePoint URLs into Host, Site Path, and File Path
        # Captures: https://{host}(/sites/{sitename} OR /)({remaining_file_path})
        self.url_pattern = re.compile(r"https://(?P<host>[^/]+)(?P<site_path>(?:/sites/[^/]+)|/)(?P<file_path>/.*)")
        self._authenticate()

    def _authenticate(self):
        """Authenticates using Client Credentials flow with retry logic recommendation."""
        try:
            # In highly robust scenarios, wrap this in a retry decorator (e.g., tenancy)
            # to handle transient AAD failures during container startup.
            app = msal.ConfidentialClientApplication(
                self.client_id, authority=self.authority, client_credential=self.client_secret
            )
            result = app.acquire_token_for_client(scopes=self.scope)
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Successfully authenticated with MS Graph.")
            else:
                error_description = result.get('error_description', 'Unknown Error')
                logger.error(f"Error acquiring token: {error_description}")
                raise Exception(f"Failed to authenticate with MS Graph: {result.get('error')}")
        except Exception as e:
            logger.critical("Critical authentication failure.")
            raise

    def _get_headers(self) -> Dict[str, str]:
        # Ensure token is present before making calls
        if not self.access_token:
             self._authenticate()
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def fetch_list_items(self, site_id: str, list_id: str) -> List[Dict[str, Any]]:
        """Fetches metadata from the SharePoint Master List, handling pagination."""
        # Validate inputs to prevent useless API calls
        if not site_id or not list_id:
             logger.error("Missing site_id or list_id for fetching list items.")
             return []

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields"
        items = []
        
        logger.info(f"Starting fetch of list items. Site: {site_id}, List: {list_id}")
        page_count = 0
        while url:
            try:
                page_count += 1
                response = requests.get(url, headers=self._get_headers(), timeout=30)
                response.raise_for_status()
                data = response.json()
                current_page_items = data.get('value', [])
                items.extend(current_page_items)
                
                # Handle pagination (@odata.nextLink)
                url = data.get('@odata.nextLink')
                if url: logger.debug(f"Fetching page {page_count+1} of list items...")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch list items on page {page_count}: {e}")
                if e.response: logger.error(f"API Response info: {e.response.text}")
                raise
                
        logger.info(f"Completed fetch. Total items retrieved: {len(items)}.")
        return items

    def fetch_page_content(self, page_url: str) -> str:
        """
        Fetches raw HTML content by resolving a human-readable SP URL to Graph API endpoints.
        Implementation uses a 2-step resolution process.
        """
        logger.info(f"Attempting to resolve and fetch content for URL: {page_url}")

        # 1. Parse the URL structure
        match = self.url_pattern.match(page_url)
        if not match:
             raise ValueError(f"Provided URL does not match expected SharePoint structure: {page_url}")

        host = match.group("host")
        site_path_raw = match.group("site_path")
        # Normalize site path (remove trailing slash unless it's root /)
        site_path = site_path_raw.rstrip('/') if len(site_path_raw) > 1 else site_path_raw
        # IMPORTANT: Unquote file path to handle URL encoded spaces (%20) -> actual spaces
        file_path = unquote(match.group("file_path"))

        logger.debug(f"Parsed URL - Host: {host}, SitePath: {site_path}, FilePath: {file_path}")

        try:
            # 2. Step 1: Resolve Site ID using Host and Site Path
            # API format: GET /sites/{hostname}:/{server-relative-path}
            # This tells Graph API to look up the site by path convention.
            site_lookup_url = f"https://graph.microsoft.com/v1.0/sites/{host}:{site_path}"
            logger.debug(f"Resolving Site ID via: {site_lookup_url}")
            
            site_resp = requests.get(site_lookup_url, headers=self._get_headers(), timeout=20)
            site_resp.raise_for_status()
            site_data = site_resp.json()
            site_id = site_data.get('id')

            if not site_id:
                 raise Exception(f"Graph API returned success but no Site ID for path: {site_path}")

            # 3. Step 2: Fetch File Content using resolved Site ID and relative file path
            # API format: GET /sites/{site-id}/drive/root:/{path-to-file}:/content
            # We address the 'root' drive of the site (usually documents or site pages) by path.
            content_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:{file_path}:/content"
            logger.info(f"Fetching file stream from resolved Graph URL: {content_url}")

            # Note: /content endpoints often return a 302 Redirect to a temp storage location.
            # requests handles redirects automatically by default. 
            # We use stream=True for efficient handling of potentially large responses, though pages are usually small.
            content_resp = requests.get(content_url, headers=self._get_headers(), timeout=60, stream=True)
            content_resp.raise_for_status()

            # Return text content. Requests will decode based on response headers (usually utf-8 for ASPX)
            return content_resp.text

        except requests.exceptions.HTTPError as e:
             if e.response.status_code == 404:
                  logger.error(f"Page or Site not found via Graph API: {page_url}")
             else:
                  logger.error(f"Graph API HTTP error fetching page {page_url}: {e}")
                  if e.response: logger.debug(f"Error details: {e.response.text}")
             raise
        except Exception as e:
             logger.error(f"Unexpected error resolving/fetching page {page_url}: {e}")
             raise

    def download_image_bytes(self, image_url: str) -> Optional[bytes]:
        """Downloads image data from SharePoint, handling potential redirects."""
        if not image_url:
             return None
        try:
            # Similar to page content, image downloads often redirect.
            # Ensure we are using a Graph-compatible URL or resolving it if necessary.
            # Assuming here image_url is already a valid downloadable endpoint or simple SP URL.
            logger.debug(f"Attempting to download image: {image_url}")
            response = requests.get(image_url, headers=self._get_headers(), timeout=60, stream=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            # Log as warning, don't fail the pipeline for a single broken image
            logger.warning(f"Failed to download image {image_url}. Details: {e}")
            return None