"""
SharePoint Publisher Module

Converts markdown documentation to SharePoint modern pages (.aspx)
and publishes them using MS Graph API.
"""

import os
import re
import json
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, field

import aiohttp
import msal

logger = logging.getLogger(__name__)


@dataclass
class SharePointPageConfig:
    """Configuration for SharePoint page publishing."""
    site_id: str
    tenant_id: str
    client_id: str
    client_secret: str
    target_folder: str = "Generated Documentation"
    page_template: str = "Article"  # Article, Home, SingleWebPartAppPage
    promote_as_news: bool = False
    
    @classmethod
    def from_env(cls) -> "SharePointPageConfig":
        """Create configuration from environment variables."""
        return cls(
            site_id=os.getenv("SHAREPOINT_SITE_ID", ""),
            tenant_id=os.getenv("AZURE_TENANT_ID", os.getenv("SHAREPOINT_TENANT_ID", "")),
            client_id=os.getenv("AZURE_CLIENT_ID", os.getenv("SHAREPOINT_CLIENT_ID", "")),
            client_secret=os.getenv("AZURE_CLIENT_SECRET", os.getenv("SHAREPOINT_CLIENT_SECRET", "")),
            target_folder=os.getenv("SHAREPOINT_TARGET_FOLDER", "Generated Documentation"),
            page_template=os.getenv("SHAREPOINT_PAGE_TEMPLATE", "Article"),
            promote_as_news=os.getenv("SHAREPOINT_PROMOTE_AS_NEWS", "false").lower() == "true"
        )
    
    def is_valid(self) -> bool:
        """Check if configuration has required values."""
        return bool(self.site_id and self.tenant_id and self.client_id and self.client_secret)


@dataclass
class PublishResult:
    """Result of a SharePoint publish operation."""
    success: bool
    page_id: Optional[str] = None
    page_url: Optional[str] = None
    error: Optional[str] = None
    publish_time_ms: int = 0


class MarkdownToSharePointConverter:
    """
    Converts markdown content to SharePoint modern page format.
    
    SharePoint modern pages use a specific JSON structure for web parts.
    """
    
    def __init__(self):
        self.web_part_id_counter = 0
    
    def _generate_web_part_id(self) -> str:
        """Generate unique web part instance ID."""
        self.web_part_id_counter += 1
        unique_hash = hashlib.md5(f"{datetime.now()}-{self.web_part_id_counter}".encode()).hexdigest()[:8]
        return f"wp-{self.web_part_id_counter}-{unique_hash}"
    
    def markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown to HTML suitable for SharePoint.
        
        Handles:
        - Headers (h1-h6)
        - Bold/italic
        - Code blocks
        - Lists (ordered/unordered)
        - Links
        """
        html = markdown_text
        
        # Escape HTML entities first (but not our generated tags)
        # We'll handle this carefully to avoid double-escaping
        
        # Code blocks (fenced) - process first to protect content
        code_blocks = []
        def save_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            # Escape HTML in code
            code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
            return placeholder
        
        html = re.sub(r'```(\w+)?\n(.*?)```', save_code_block, html, flags=re.DOTALL)
        
        # Inline code
        def escape_inline_code(match):
            code = match.group(1)
            code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f'<code>{code}</code>'
        
        html = re.sub(r'`([^`]+)`', escape_inline_code, html)
        
        # Headers (process h6 to h1 to avoid conflicts)
        for i in range(6, 0, -1):
            pattern = r'^' + '#' * i + r' (.+)$'
            html = re.sub(pattern, f'<h{i}>\\1</h{i}>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', html)
        
        # Italic
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
        html = re.sub(r'_([^_]+)_', r'<em>\1</em>', html)
        
        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # Unordered lists - collect consecutive items
        lines = html.split('\n')
        processed_lines = []
        in_list = False
        list_items = []
        
        for line in lines:
            ul_match = re.match(r'^[-*+] (.+)$', line)
            ol_match = re.match(r'^\d+\. (.+)$', line)
            
            if ul_match:
                if not in_list:
                    in_list = 'ul'
                    list_items = []
                list_items.append(f'<li>{ul_match.group(1)}</li>')
            elif ol_match:
                if not in_list:
                    in_list = 'ol'
                    list_items = []
                list_items.append(f'<li>{ol_match.group(1)}</li>')
            else:
                if in_list:
                    tag = in_list
                    processed_lines.append(f'<{tag}>{"".join(list_items)}</{tag}>')
                    in_list = False
                    list_items = []
                
                # Regular line - wrap in paragraph if not already tagged
                stripped = line.strip()
                if stripped and not stripped.startswith('<') and not stripped.startswith('__CODE_BLOCK_'):
                    processed_lines.append(f'<p>{stripped}</p>')
                elif stripped:
                    processed_lines.append(line)
        
        # Handle list at end of content
        if in_list:
            tag = in_list
            processed_lines.append(f'<{tag}>{"".join(list_items)}</{tag}>')
        
        html = '\n'.join(processed_lines)
        
        # Restore code blocks
        for i, block in enumerate(code_blocks):
            html = html.replace(f'__CODE_BLOCK_{i}__', block)
        
        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)
        
        return html
    
    def create_text_web_part(self, html_content: str) -> dict:
        """Create a SharePoint Text web part structure."""
        return {
            "id": self._generate_web_part_id(),
            "innerHtml": html_content
        }
    
    def create_section(self, web_parts: List[dict], column_layout: str = "oneColumn") -> dict:
        """
        Create a SharePoint page section.
        
        column_layout options: oneColumn, twoColumns, threeColumns, 
                               oneThirdLeftColumn, oneThirdRightColumn
        """
        columns = []
        
        if column_layout == "oneColumn":
            columns = [{
                "factor": 12,
                "webparts": web_parts
            }]
        elif column_layout == "twoColumns":
            mid = len(web_parts) // 2 or 1
            columns = [
                {"factor": 6, "webparts": web_parts[:mid]},
                {"factor": 6, "webparts": web_parts[mid:]}
            ]
        else:
            columns = [{
                "factor": 12,
                "webparts": web_parts
            }]
        
        return {
            "columns": columns,
            "emphasis": "none"
        }
    
    def convert_document(self, sections: Dict[str, str], title: str) -> dict:
        """
        Convert a complete document with multiple sections to SharePoint page structure.
        
        Args:
            sections: Dictionary of section_name -> markdown_content
            title: Page title
            
        Returns:
            SharePoint page canvas content structure
        """
        page_sections = []
        
        for section_name, markdown_content in sections.items():
            # Skip metadata sections (internal use)
            if section_name.startswith('_'):
                continue
            
            # Convert markdown to HTML
            html_content = self.markdown_to_html(markdown_content)
            
            # Create web part for this section
            web_part = self.create_text_web_part(html_content)
            
            # Create page section
            section = self.create_section([web_part])
            page_sections.append(section)
        
        return {
            "canvasLayout": {
                "horizontalSections": page_sections
            }
        }


class SharePointPublisher:
    """
    Publishes documentation to SharePoint using MS Graph API.
    
    Uses modern page API to create and publish .aspx pages.
    """
    
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    GRAPH_BETA_URL = "https://graph.microsoft.com/beta"  # Some page APIs require beta
    
    def __init__(self, config: SharePointPageConfig):
        self.config = config
        self.converter = MarkdownToSharePointConverter()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._msal_app: Optional[msal.ConfidentialClientApplication] = None
    
    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL application instance."""
        if self._msal_app is None:
            authority = f"https://login.microsoftonline.com/{self.config.tenant_id}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=authority
            )
        return self._msal_app
    
    async def _ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        if (self._access_token is None or 
            self._token_expires_at is None or
            datetime.now() >= self._token_expires_at - timedelta(minutes=5)):
            
            logger.info("Acquiring new access token for MS Graph API")
            
            app = self._get_msal_app()
            
            # Run MSAL token acquisition in thread pool (it's synchronous)
            result = await asyncio.to_thread(
                app.acquire_token_for_client,
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                self._access_token = result["access_token"]
                # Token typically expires in 1 hour
                expires_in = result.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                logger.info(f"Token acquired, expires in {expires_in} seconds")
            else:
                error = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Failed to acquire token: {error}")
        
        return self._access_token
    
    def _get_headers(self, token: str) -> dict:
        """Get HTTP headers for Graph API requests."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _request_with_retry(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: dict,
        json_body: Optional[dict] = None,
        max_retries: int = 3
    ) -> tuple:
        """Make HTTP request with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    async with session.get(url, headers=headers) as response:
                        return response.status, await response.text()
                elif method == "POST":
                    async with session.post(url, headers=headers, json=json_body) as response:
                        return response.status, await response.text()
                elif method == "PATCH":
                    async with session.patch(url, headers=headers, json=json_body) as response:
                        return response.status, await response.text()
                        
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
        
        raise last_error
    
    async def create_page(
        self,
        session: aiohttp.ClientSession,
        title: str,
        description: str = ""
    ) -> dict:
        """
        Create a new SharePoint modern page.
        
        Args:
            session: aiohttp session
            title: Page title
            description: Optional page description
            
        Returns:
            Created page metadata
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Generate safe page name from title
        page_name = re.sub(r'[^\w\s-]', '', title).strip()
        page_name = re.sub(r'[-\s]+', '-', page_name).lower()
        page_name = f"{page_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}.aspx"
        
        # Create page request body
        page_body = {
            "name": page_name,
            "title": title,
            "pageLayout": self.config.page_template.lower()
        }
        
        if description:
            page_body["description"] = description
        
        # Create the page
        url = f"{self.GRAPH_BETA_URL}/sites/{self.config.site_id}/pages"
        
        status, response_text = await self._request_with_retry(
            session, "POST", url, headers, page_body
        )
        
        if status == 201:
            page_data = json.loads(response_text)
            logger.info(f"Created page: {page_data.get('id')} - {page_data.get('name')}")
            return page_data
        else:
            raise Exception(f"Failed to create page: {status} - {response_text}")
    
    async def set_page_content(
        self,
        session: aiohttp.ClientSession,
        page_id: str,
        sections: Dict[str, str],
        title: str
    ) -> bool:
        """
        Set the content of a SharePoint page using canvas content.
        
        Args:
            session: aiohttp session
            page_id: The ID of the page to update
            sections: Dictionary of section_name -> markdown_content
            title: Page title for conversion
            
        Returns:
            True if successful
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Convert sections to SharePoint canvas format
        canvas_content = self.converter.convert_document(sections, title)
        
        # Update page content
        url = f"{self.GRAPH_BETA_URL}/sites/{self.config.site_id}/pages/{page_id}"
        
        update_body = {
            "canvasLayout": canvas_content["canvasLayout"]
        }
        
        status, response_text = await self._request_with_retry(
            session, "PATCH", url, headers, update_body
        )
        
        if status in (200, 204):
            logger.info(f"Updated page content for page ID: {page_id}")
            return True
        else:
            raise Exception(f"Failed to update page content: {status} - {response_text}")
    
    async def publish_page(
        self,
        session: aiohttp.ClientSession,
        page_id: str
    ) -> str:
        """
        Publish a SharePoint page, making it visible to users.
        
        Args:
            session: aiohttp session
            page_id: The ID of the page to publish
            
        Returns:
            Published page URL
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Publish the page
        url = f"{self.GRAPH_BETA_URL}/sites/{self.config.site_id}/pages/{page_id}/publish"
        
        status, response_text = await self._request_with_retry(
            session, "POST", url, headers
        )
        
        if status in (200, 204):
            logger.info(f"Published page: {page_id}")
        else:
            raise Exception(f"Failed to publish page: {status} - {response_text}")
        
        # Get the page URL
        page_url = f"{self.GRAPH_BETA_URL}/sites/{self.config.site_id}/pages/{page_id}"
        
        status, response_text = await self._request_with_retry(
            session, "GET", page_url, headers
        )
        
        if status == 200:
            page_data = json.loads(response_text)
            return page_data.get("webUrl", "")
        else:
            return ""
    
    async def promote_as_news(
        self,
        session: aiohttp.ClientSession,
        page_id: str
    ) -> bool:
        """
        Promote a page as a news article.
        
        Args:
            session: aiohttp session
            page_id: The ID of the page to promote
            
        Returns:
            True if successful
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        url = f"{self.GRAPH_BETA_URL}/sites/{self.config.site_id}/pages/{page_id}"
        
        update_body = {
            "promotionKind": "newsPost"
        }
        
        status, response_text = await self._request_with_retry(
            session, "PATCH", url, headers, update_body
        )
        
        if status in (200, 204):
            logger.info(f"Promoted page as news: {page_id}")
            return True
        else:
            logger.warning(f"Failed to promote as news: {status} - {response_text}")
            return False
    
    async def ensure_folder_exists(
        self,
        session: aiohttp.ClientSession,
        folder_path: str
    ) -> bool:
        """
        Ensure target folder exists in Site Pages library.
        
        Args:
            session: aiohttp session
            folder_path: Target folder path
            
        Returns:
            True if folder exists or was created
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Check if folder exists
        folder_url = f"{self.GRAPH_BASE_URL}/sites/{self.config.site_id}/drive/root:/SitePages/{folder_path}"
        
        status, _ = await self._request_with_retry(
            session, "GET", folder_url, headers
        )
        
        if status == 200:
            return True
        
        if status == 404:
            # Create the folder
            create_folder_url = f"{self.GRAPH_BASE_URL}/sites/{self.config.site_id}/drive/root:/SitePages:/children"
            folder_body = {
                "name": folder_path,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"
            }
            
            status, response_text = await self._request_with_retry(
                session, "POST", create_folder_url, headers, folder_body
            )
            
            if status in (200, 201):
                logger.info(f"Created folder: {folder_path}")
                return True
            else:
                logger.warning(f"Could not create folder: {folder_path} - {response_text}")
                return False
        
        return False
    
    async def publish_document(
        self,
        title: str,
        sections: Dict[str, str],
        description: str = "",
        diagram_description: str = "",
        donor_pattern: str = ""
    ) -> PublishResult:
        """
        Complete workflow to publish a document to SharePoint.
        
        This is the main entry point for the Orchestrator to call.
        
        Args:
            title: Page title
            sections: Dictionary of section_name -> markdown_content
            description: Optional page description
            diagram_description: Description of the analyzed diagram
            donor_pattern: ID of the donor pattern used
            
        Returns:
            PublishResult with success status and page URL
        """
        start_time = datetime.now()
        
        # Validate configuration
        if not self.config.is_valid():
            return PublishResult(
                success=False,
                error="SharePoint configuration is incomplete. Check SHAREPOINT_SITE_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET."
            )
        
        # Add metadata section to the document
        sections_with_metadata = dict(sections)
        if diagram_description or donor_pattern:
            metadata_md = "\n\n---\n\n## Document Metadata\n\n"
            if diagram_description:
                # Truncate long descriptions
                desc_preview = diagram_description[:500]
                if len(diagram_description) > 500:
                    desc_preview += "..."
                metadata_md += f"**Source Diagram Analysis:**\n{desc_preview}\n\n"
            if donor_pattern:
                metadata_md += f"**Reference Pattern:** {donor_pattern}\n\n"
            metadata_md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            sections_with_metadata["Document Metadata"] = metadata_md
        
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Ensure target folder exists (optional)
                if self.config.target_folder:
                    logger.info(f"Ensuring folder exists: {self.config.target_folder}")
                    await self.ensure_folder_exists(session, self.config.target_folder)
                
                # Step 2: Create the page
                logger.info(f"Creating SharePoint page: {title}")
                page_data = await self.create_page(
                    session=session,
                    title=title,
                    description=description or f"Architecture documentation for {title}"
                )
                page_id = page_data["id"]
                
                # Step 3: Set page content
                logger.info(f"Setting page content for: {page_id}")
                await self.set_page_content(
                    session=session,
                    page_id=page_id,
                    sections=sections_with_metadata,
                    title=title
                )
                
                # Step 4: Publish the page
                logger.info(f"Publishing page: {page_id}")
                page_url = await self.publish_page(
                    session=session,
                    page_id=page_id
                )
                
                # Step 5: Promote as news (if configured)
                if self.config.promote_as_news:
                    logger.info(f"Promoting as news: {page_id}")
                    await self.promote_as_news(
                        session=session,
                        page_id=page_id
                    )
                
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                logger.info(f"Successfully published page: {page_url} in {elapsed_ms}ms")
                
                return PublishResult(
                    success=True,
                    page_id=page_id,
                    page_url=page_url,
                    publish_time_ms=elapsed_ms
                )
                
        except Exception as e:
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Failed to publish to SharePoint: {str(e)}", exc_info=True)
            
            return PublishResult(
                success=False,
                error=str(e),
                publish_time_ms=elapsed_ms
            )
