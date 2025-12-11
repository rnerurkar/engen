"""
SharePoint Publisher Module
============================

This module converts markdown documentation to SharePoint modern pages (.aspx)
and publishes them using the Microsoft Graph API.

OVERVIEW FOR BEGINNERS
----------------------

What This Module Does (High-Level):
1. Takes markdown text (like README files with # headers, **bold**, `code`, etc.)
2. Converts it to HTML (the language web browsers understand)
3. Wraps that HTML in SharePoint's special "web part" format
4. Sends it to SharePoint via Microsoft Graph API to create a modern page

Key Concepts:
- Markdown: A simple text format using symbols like # for headers, ** for bold
- HTML: The language of web pages (<h1>, <p>, <strong> tags)
- Web Parts: SharePoint's building blocks for page content
- MS Graph API: Microsoft's REST API for accessing SharePoint, Teams, etc.
- OAuth: Authentication method using tokens instead of passwords

CONVERSION PIPELINE:
   Markdown → HTML → Web Part JSON → SharePoint Page Canvas → Published Page

Example Flow:
   "## Problem\n\nThis is **important**."
         ↓ (markdown_to_html)
   "<h2>Problem</h2><p>This is <strong>important</strong>.</p>"
         ↓ (create_text_web_part)
   {"id": "wp-1-abc", "innerHtml": "<h2>Problem</h2>..."}
         ↓ (create_section)
   {"columns": [{"factor": 12, "webparts": [...]}]}
         ↓ (MS Graph API POST)
   https://company.sharepoint.com/sites/MySite/SitePages/my-doc.aspx
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
import random

# Third-party libraries for robust markdown conversion and sanitization
try:
    import markdown as md
except ImportError:  # pragma: no cover
    md = None
try:
    import bleach
except ImportError:  # pragma: no cover
    bleach = None

logger = logging.getLogger(__name__)


@dataclass
class SharePointPageConfig:
    """
    Configuration for SharePoint page publishing.
    
    This dataclass holds all the credentials and settings needed to connect
    to SharePoint via Microsoft Graph API.
    
    REQUIRED ENVIRONMENT VARIABLES:
    --------------------------------
    SHAREPOINT_SITE_ID    : The unique ID of your SharePoint site
                            Find it: /_api/site/id in your SharePoint site
    AZURE_TENANT_ID       : Your Microsoft 365 tenant ID (a GUID)
                            Find it: Azure Portal → Azure Active Directory → Overview
    AZURE_CLIENT_ID       : The Application (client) ID of your Azure AD app
                            Find it: Azure Portal → App Registrations → Your App
    AZURE_CLIENT_SECRET   : A secret key for your Azure AD app
                            Create it: Azure Portal → App Registrations → Certificates & secrets
    
    OPTIONAL ENVIRONMENT VARIABLES:
    --------------------------------
    SHAREPOINT_TARGET_FOLDER : Folder name under SitePages (default: "Generated Documentation")
    SHAREPOINT_PAGE_TEMPLATE : Page layout type (default: "Article")
                               Options: Article, Home, SingleWebPartAppPage
    SHAREPOINT_PROMOTE_AS_NEWS : "true" to show in news feed (default: "false")
    
    AZURE AD APP PERMISSIONS REQUIRED:
    -----------------------------------
    Microsoft Graph (Application permissions):
    - Sites.ReadWrite.All  : Create and modify pages
    - Sites.Manage.All     : Manage site settings (for publishing)
    
    Usage Example:
    --------------
    config = SharePointPageConfig.from_env()
    if config.is_valid():
        publisher = SharePointPublisher(config)
    """
    site_id: str
    tenant_id: str
    client_id: str
    client_secret: str
    target_folder: str = "Generated Documentation"
    page_template: str = "Article"  # Article, Home, SingleWebPartAppPage
    promote_as_news: bool = False
    
    @classmethod
    def from_env(cls) -> "SharePointPageConfig":
        """
        Create configuration from environment variables.
        
        This factory method reads from os.environ and creates a config object.
        It supports legacy variable names (SHAREPOINT_TENANT_ID) as fallbacks.
        
        Returns:
            SharePointPageConfig instance populated from environment
        """
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
        """
        Check if configuration has all required values.
        
        Publishing will fail if any of these are missing:
        - site_id: Where to create the page
        - tenant_id: Which Microsoft 365 organization
        - client_id: Which app is making the request
        - client_secret: Proof that we own the app
        
        Returns:
            True if all required fields are present and non-empty
        """
        # Basic presence check
        if not (self.site_id and self.tenant_id and self.client_id and self.client_secret):
            return False
        
        # Basic format validation (GUID-like for tenant/client)
        guid_regex = re.compile(r'^[0-9a-fA-F-]{32,36}$')
        if not guid_regex.match(self.tenant_id):
            logger.warning("AZURE_TENANT_ID format may be invalid")
        if not guid_regex.match(self.client_id):
            logger.warning("AZURE_CLIENT_ID format may be invalid")
        
        return True


@dataclass
class PublishResult:
    """
    Result of a SharePoint publish operation.
    
    This dataclass is returned by publish_document() to communicate
    the outcome of the publishing attempt.
    
    Attributes:
        success      : True if page was created and published successfully
        page_id      : The unique identifier for the page in SharePoint
                       (can be used for future updates)
        page_url     : The full URL where users can view the page
                       Example: https://company.sharepoint.com/sites/MySite/SitePages/my-doc.aspx
        error        : Error message if success=False
        publish_time_ms : How long the entire operation took (in milliseconds)
    
    Success Example:
    ----------------
    PublishResult(
        success=True,
        page_id="abc123-def456",
        page_url="https://company.sharepoint.com/sites/MySite/SitePages/architecture-doc.aspx",
        error=None,
        publish_time_ms=2340
    )
    
    Failure Example:
    ----------------
    PublishResult(
        success=False,
        page_id=None,
        page_url=None,
        error="Failed to acquire token: Invalid client secret",
        publish_time_ms=150
    )
    """
    success: bool
    page_id: Optional[str] = None
    page_url: Optional[str] = None
    error: Optional[str] = None
    publish_time_ms: int = 0


class MarkdownToSharePointConverter:
    """
    Converts markdown content to SharePoint modern page format.
    
    UNDERSTANDING THE CONVERSION PROCESS
    =====================================
    
    SharePoint modern pages don't understand markdown directly. They use a
    specific JSON structure with "web parts" - reusable content blocks.
    
    This converter does 3 things:
    1. markdown_to_html()  : Convert markdown syntax to HTML tags
    2. create_text_web_part() : Wrap HTML in SharePoint's Text web part format
    3. create_section()    : Organize web parts into page sections
    
    MARKDOWN → HTML CONVERSION EXPLAINED
    =====================================
    
    Markdown uses simple symbols to format text. This converter translates
    each symbol to its HTML equivalent:
    
    | Markdown         | HTML                      | What It Does        |
    |------------------|---------------------------|---------------------|
    | # Title          | <h1>Title</h1>            | Level 1 heading     |
    | ## Subtitle      | <h2>Subtitle</h2>         | Level 2 heading     |
    | **bold**         | <strong>bold</strong>     | Bold text           |
    | *italic*         | <em>italic</em>           | Italic text         |
    | `code`           | <code>code</code>         | Inline code         |
    | ```code block``` | <pre><code>...</code></pre>| Code block         |
    | [text](url)      | <a href="url">text</a>    | Hyperlink           |
    | - item           | <ul><li>item</li></ul>    | Bullet list         |
    | 1. item          | <ol><li>item</li></ol>    | Numbered list       |
    
    REGULAR EXPRESSIONS (REGEX) PRIMER
    ===================================
    
    This class uses regex patterns to find and replace markdown syntax.
    Here's a quick reference for the regex symbols used:
    
    Symbol  | Meaning                          | Example
    --------|----------------------------------|----------------------
    ^       | Start of line                    | ^# matches "# " at line start
    $       | End of line                      | text$ matches "text" at line end
    .       | Any single character             | a.c matches "abc", "a1c"
    *       | Zero or more of previous         | ab* matches "a", "ab", "abb"
    +       | One or more of previous          | ab+ matches "ab", "abb" (not "a")
    ?       | Zero or one of previous          | ab? matches "a" or "ab"
    \\w     | Word character (letter/digit/_)  | \\w+ matches "hello"
    \\s     | Whitespace (space/tab/newline)   | \\s+ matches "   "
    \\d     | Digit (0-9)                      | \\d+ matches "123"
    [abc]   | Any char in brackets             | [aeiou] matches any vowel
    [^abc]  | Any char NOT in brackets         | [^0-9] matches non-digits
    (...)   | Capture group                    | (\\w+) captures word for later
    \\1     | Reference to group 1             | Used in replacement string
    |       | OR operator                      | cat|dog matches either
    
    REGEX FLAGS USED:
    - re.MULTILINE : ^ and $ match start/end of each line (not just string)
    - re.DOTALL    : . matches newline characters too
    
    SHAREPOINT PAGE STRUCTURE
    ==========================
    
    A SharePoint modern page is organized like this:
    
    Page
    └── canvasLayout
        └── horizontalSections[]        ← Array of horizontal bands
            └── columns[]               ← Array of columns in that band
                └── webparts[]          ← Array of web parts in that column
                    └── innerHtml       ← The actual HTML content
    
    The "factor" property determines column width (12 = full width in a 12-column grid):
    - factor: 12 = full width
    - factor: 6  = half width (for 2-column layouts)
    - factor: 4  = third width (for 3-column layouts)
    """
    
    def __init__(self):
        """
        Initialize the converter.
        
        Converter maintains no shared mutable state across calls to avoid
        concurrency issues. Web part IDs are generated using a per-call
        approach via a local counter.
        """
        self._local_counter = 0
    
    def _generate_web_part_id(self) -> str:
        """
        Generate unique web part instance ID.
        
        SharePoint requires each web part to have a unique identifier.
        This generates IDs like: "wp-1-a3f8c2b1", "wp-2-b7d9e4f2"
        
        The format is: wp-{counter}-{hash}
        - counter: Sequential number for this converter instance
        - hash: First 8 chars of MD5 hash for uniqueness
        
        Returns:
            A unique web part ID string
        """
        self._local_counter += 1
        # Create a hash from timestamp + counter for uniqueness
        unique_hash = hashlib.md5(f"{datetime.now()}-{self._local_counter}".encode()).hexdigest()[:8]
        return f"wp-{self._local_counter}-{unique_hash}"
    
    def markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown to HTML suitable for SharePoint.
        
        This is the core conversion function that transforms markdown syntax
        into HTML tags. The order of operations matters - we process elements
        from most complex (code blocks) to simplest (paragraphs).
        
        PROCESSING ORDER:
        1. Code blocks (``` ```)  - Protect these first so content isn't changed
        2. Inline code (` `)      - Single backticks for inline code
        3. Headers (# to ######)  - Process from h6 to h1 to avoid conflicts
        4. Bold (**text**)        - Double asterisks or underscores
        5. Italic (*text*)        - Single asterisks or underscores
        6. Links ([text](url))    - Hyperlinks
        7. Lists (- or 1.)        - Bullet and numbered lists
        8. Paragraphs             - Wrap remaining text in <p> tags
        
        Args:
            markdown_text: Raw markdown string
            
        Returns:
            HTML string suitable for SharePoint web part
            
        Example:
            >>> converter = MarkdownToSharePointConverter()
            >>> html = converter.markdown_to_html("## Hello\\n\\nThis is **bold**.")
            >>> print(html)
            <h2>Hello</h2>
            <p>This is <strong>bold</strong>.</p>
        """
        html = markdown_text
        
        # =====================================================================
        # STEP 1: HANDLE CODE BLOCKS FIRST
        # =====================================================================
        # Code blocks are fenced with triple backticks: ```language\ncode\n```
        # We extract these first to protect their content from other conversions.
        # 
        # REGEX EXPLAINED: r'```(\\w+)?\\n(.*?)```'
        #   ```       - Literal triple backticks (start of code block)
        def markdown_to_html(self, markdown_text: str) -> str:
            """
            Convert markdown to HTML suitable for SharePoint using a robust library
            and sanitize the output for safety.
        
            Uses `markdown` with common extensions:
            - fenced_code, codehilite, tables, sane_lists, toc
            Then sanitizes with `bleach` to allow only safe tags/attributes.
        
            Falls back to the existing regex converter if libraries are missing.
            """
            # If markdown library is available, prefer it
            if md is not None:
                extensions = [
                    'fenced_code', 'codehilite', 'tables', 'sane_lists', 'toc'
                ]
                html = md.markdown(markdown_text or '', extensions=extensions)
            else:
                html = markdown_text or ''
        
            # Sanitize with bleach if available
            if bleach is not None:
                allowed_tags = [
                    'h1','h2','h3','h4','h5','h6','p','strong','em','ul','ol','li',
                    'code','pre','blockquote','a','table','thead','tbody','tr','th','td',
                    'hr','br','span','div'
                ]
                allowed_attrs = {
                    'a': ['href','title','target','rel'],
                    'code': ['class'],
                    'span': ['class'],
                    'div': ['class']
                }
                html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
        
            return html
    
    def create_text_web_part(self, html_content: str) -> dict:
        """
        Create a SharePoint Text web part structure using the modern schema.
        
        SharePoint Text web part schema typically includes:
        - id / instanceId: unique identifiers
        - dataVersion: content schema version
        - properties: object with `inlineHtml`
        
        This aligns closer to SharePoint expectations than raw `innerHtml`.
        """
        instance_id = self._generate_web_part_id()
        return {
            "id": instance_id,
            "instanceId": instance_id,
            "dataVersion": "1.0",
            "properties": {
                "inlineHtml": html_content
            }
        }
    
    def create_section(self, web_parts: List[dict], column_layout: str = "oneColumn") -> dict:
        """
        Create a SharePoint page section.
        
        UNDERSTANDING PAGE SECTIONS
        ----------------------------
        SharePoint pages are divided into horizontal "sections" (bands across the page).
        Each section can have one or more columns.
        
        SharePoint uses a 12-column grid system (like Bootstrap):
        - factor: 12 = full width (100%)
        - factor: 6  = half width (50%) 
        - factor: 4  = third width (33%)
        - factor: 3  = quarter width (25%)
        
        LAYOUT OPTIONS:
        ---------------
        - "oneColumn"          : Single full-width column (factor: 12)
        - "twoColumns"         : Two equal columns (factor: 6 each)
        - "threeColumns"       : Three equal columns (factor: 4 each)
        - "oneThirdLeftColumn" : Narrow left, wide right
        - "oneThirdRightColumn": Wide left, narrow right
        
        The returned structure looks like:
        {
            "columns": [
                {"factor": 12, "webparts": [...]}
            ],
            "emphasis": "none"   ← Background style (none, neutral, soft, strong)
        }
        
        Args:
            web_parts: List of web part dictionaries to include
            column_layout: How to arrange columns
            
        Returns:
            Dictionary representing a page section
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
        
        THE FULL CONVERSION PIPELINE
        =============================
        
        This method orchestrates the entire conversion process:
        
        INPUT (sections dictionary):
        {
            "Problem": "## Problem\\n\\nThe system has **issues**...",
            "Solution": "## Solution\\n\\nWe propose to..."
        }
        
        STEP 1: For each section, convert markdown to HTML:
        {
            "Problem": "<h2>Problem</h2><p>The system has <strong>issues</strong>...</p>",
            "Solution": "<h2>Solution</h2><p>We propose to...</p>"
        }
        
        STEP 2: Wrap each HTML in a Text web part:
        [
            {"id": "wp-1-abc", "innerHtml": "<h2>Problem</h2>..."},
            {"id": "wp-2-def", "innerHtml": "<h2>Solution</h2>..."}
        ]
        
        STEP 3: Wrap web parts in page sections:
        [
            {"columns": [{"factor": 12, "webparts": [wp1]}], "emphasis": "none"},
            {"columns": [{"factor": 12, "webparts": [wp2]}], "emphasis": "none"}
        ]
        
        STEP 4: Wrap sections in canvas layout:
        {
            "canvasLayout": {
                "horizontalSections": [section1, section2]
            }
        }
        
        This final structure is what SharePoint's Graph API expects.
        
        Args:
            sections: Dictionary of section_name -> markdown_content
                      Example: {"Problem": "## Problem\\n...", "Solution": "..."}
            title: Page title (not used in conversion, but may be useful for headers)
            
        Returns:
            SharePoint page canvas content structure ready for Graph API
        """
        page_sections = []
        
        for section_name, markdown_content in sections.items():
            # Skip metadata sections (internal use) - sections starting with _
            # are reserved for internal metadata like "_generated_by"
            if section_name.startswith('_'):
                continue
            
            # Convert markdown to HTML
            html_content = self.markdown_to_html(markdown_content)
            
            # Create web part for this section
            web_part = self.create_text_web_part(html_content)
            
            # Create page section (each document section becomes a page section)
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
    
    WHAT IS MICROSOFT GRAPH API?
    =============================
    Microsoft Graph is a REST API that provides access to Microsoft 365 services:
    - SharePoint (sites, pages, documents)
    - Teams (channels, messages)
    - Outlook (email, calendar)
    - Azure AD (users, groups)
    
    Base URL: https://graph.microsoft.com/v1.0 (stable)
              https://graph.microsoft.com/beta (preview features)
    
    AUTHENTICATION FLOW (OAuth 2.0 Client Credentials)
    ===================================================
    This class uses "Application" permissions (app-only, no user login):
    
    1. Register an app in Azure AD
    2. Grant it Sites.ReadWrite.All and Sites.Manage.All permissions
    3. Create a client secret
    4. Use MSAL library to exchange client_id + client_secret for access token
    5. Include access token in HTTP Authorization header
    
    Token request flow:
    POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
    Body: grant_type=client_credentials&client_id=...&client_secret=...&scope=https://graph.microsoft.com/.default
    
    Response: {"access_token": "eyJ0...", "expires_in": 3600, ...}
    
    PAGE CREATION WORKFLOW
    =======================
    1. Create draft page: POST /sites/{siteId}/pages
    2. Set content: PATCH /sites/{siteId}/pages/{pageId}
    3. Publish: POST /sites/{siteId}/pages/{pageId}/publish
    4. (Optional) Promote as news: PATCH with {"promotionKind": "newsPost"}
    
    Uses modern page API to create and publish .aspx pages.
    """
    
    # Graph API endpoints - v1.0 for stable, beta for page-specific features
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    GRAPH_BETA_URL = "https://graph.microsoft.com/beta"  # Some page APIs require beta

    def _pages_base(self) -> str:
        """Select appropriate pages base URL (prefer v1.0, fallback to beta)."""
        # As of writing, some modern page operations are only available in beta.
        # Centralize the selection for easier control.
        return self.GRAPH_BETA_URL
    
    def __init__(self, config: SharePointPageConfig):
        """
        Initialize the SharePoint publisher.
        
        Args:
            config: SharePointPageConfig with credentials and settings
            
        The publisher maintains:
        - config: Connection configuration
        - converter: MarkdownToSharePointConverter instance for content conversion
        - _access_token: Cached OAuth token (refreshed when expired)
        - _token_expires_at: When the current token expires
        - _msal_app: MSAL library app instance for token management
        """
        self.config = config
        self.converter = MarkdownToSharePointConverter()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._msal_app: Optional[msal.ConfidentialClientApplication] = None
    
    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """
        Get or create MSAL (Microsoft Authentication Library) application instance.
        
        WHAT IS MSAL?
        -------------
        MSAL is Microsoft's library for handling OAuth authentication.
        It manages token acquisition, caching, and refresh automatically.
        
        We use ConfidentialClientApplication because:
        - We're a server-side application (not a browser)
        - We have a client secret (confidential)
        - We use Client Credentials flow (no user login)
        
        The "authority" URL tells MSAL which Azure AD tenant to authenticate against.
        
        Returns:
            MSAL ConfidentialClientApplication instance
        """
        if self._msal_app is None:
            # Authority format: https://login.microsoftonline.com/{tenant_id}
            authority = f"https://login.microsoftonline.com/{self.config.tenant_id}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=authority
            )
        return self._msal_app
    
    async def _ensure_valid_token(self) -> str:
        """
        Ensure we have a valid access token, refreshing if needed.
        
        TOKEN LIFECYCLE
        ----------------
        - Tokens typically expire after 1 hour (3600 seconds)
        - We refresh 5 minutes before expiry to avoid race conditions
        - MSAL handles the actual token request to Azure AD
        
        CLIENT CREDENTIALS FLOW
        ------------------------
        POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
        Content-Type: application/x-www-form-urlencoded
        
        Body:
        grant_type=client_credentials
        client_id={our_app_id}
        client_secret={our_secret}
        scope=https://graph.microsoft.com/.default
        
        The ".default" scope means "give me all the permissions this app has been granted"
        
        Returns:
            Valid access token string
            
        Raises:
            Exception: If token acquisition fails (invalid credentials, permissions, etc.)
        """
        # Check if we need a new token:
        # - No token yet
        # - No expiry time recorded
        # - Token expires within 5 minutes
        if not hasattr(self, "_token_lock"):
            self._token_lock = asyncio.Lock()
        
        if (self._access_token is None or 
            self._token_expires_at is None or
            datetime.now() >= self._token_expires_at - timedelta(minutes=5)):
            async with self._token_lock:
                # Double-check under lock
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
                        logger.info("Token acquired; expires in %ss", expires_in)
                    else:
                        error = result.get("error_description", result.get("error", "Unknown error"))
                        raise Exception("Failed to acquire token: %s", error)
        
        return self._access_token
    
    def _get_headers(self, token: str) -> dict:
        """
        Get HTTP headers for Graph API requests.
        
        REQUIRED HEADERS FOR MS GRAPH
        ------------------------------
        - Authorization: Bearer {token}  ← Proves we're authenticated
        - Content-Type: application/json ← We're sending JSON body
        - Accept: application/json       ← We want JSON responses
        
        Args:
            token: OAuth access token from _ensure_valid_token()
            
        Returns:
            Dictionary of HTTP headers
        """
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
        """
        Make HTTP request with robust retry logic for transient failures and throttling.
        
        Enhancements:
        - Retries on aiohttp.ClientError
        - Retries on HTTP 429 (respect Retry-After) and 502/503/504 with exponential backoff + jitter
        - Returns (status, text) for caller to parse; logs minimal info to avoid leaking secrets
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    async with session.get(url, headers=headers) as response:
                        status = response.status
                        text = await response.text()
                elif method == "POST":
                    async with session.post(url, headers=headers, json=json_body) as response:
                        status = response.status
                        text = await response.text()
                elif method == "PATCH":
                    async with session.patch(url, headers=headers, json=json_body) as response:
                        status = response.status
                        text = await response.text()
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Throttling or transient server errors
                if status in (429, 502, 503, 504) and attempt < max_retries - 1:
                    retry_after = 0
                    try:
                        # Honor Retry-After header if present
                        retry_after_header = response.headers.get('Retry-After')
                        if retry_after_header:
                            retry_after = int(retry_after_header)
                    except Exception:
                        retry_after = 0
                    base_delay = (2 ** attempt)
                    jitter = random.uniform(0, 0.5)
                    delay = max(retry_after, base_delay + jitter)
                    await asyncio.sleep(delay)
                    continue
                
                return status, text
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < max_retries - 1:
                    base_delay = (2 ** attempt)
                    jitter = random.uniform(0, 0.5)
                    await asyncio.sleep(base_delay + jitter)
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
        Create a new SharePoint modern page (Step 1 of publishing workflow).
        
        MS GRAPH API CALL
        ------------------
        POST https://graph.microsoft.com/beta/sites/{siteId}/pages
        
        Request Body:
        {
            "name": "my-document-20251211143052.aspx",
            "title": "My Document",
            "pageLayout": "article"
        }
        
        Response (201 Created):
        {
            "id": "abc123",
            "name": "my-document-20251211143052.aspx",
            "webUrl": "https://company.sharepoint.com/sites/site/SitePages/...",
            "createdDateTime": "2025-12-11T14:30:52Z",
            ...
        }
        
        PAGE NAME GENERATION
        ---------------------
        SharePoint requires a URL-safe filename. We transform the title:
        
        "Architecture: Design Patterns!"
           ↓ (remove special chars)
        "Architecture Design Patterns"
           ↓ (replace spaces with hyphens)
        "architecture-design-patterns"
           ↓ (add timestamp for uniqueness)
        "architecture-design-patterns-20251211143052.aspx"
        
        REGEX EXPLAINED:
        - r'[^\\w\\s-]' : Match anything that's NOT a word char, space, or hyphen
        - r'[-\\s]+'    : Match one or more hyphens or spaces
        
        Args:
            session: aiohttp session
            title: Page title (displayed to users)
            description: Optional page description
            
        Returns:
            Created page metadata dictionary with id, name, webUrl, etc.
            
        Raises:
            Exception: If page creation fails (permissions, invalid site, etc.)
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # =====================================================================
        # GENERATE SAFE PAGE FILENAME
        # =====================================================================
        # SharePoint filenames can't contain: " * : < > ? / \ |
        # We remove all special chars and convert spaces to hyphens
        # =====================================================================
        
        # Step 1: Remove all characters except letters, digits, spaces, and hyphens
        # Regex: [^\w\s-] matches anything NOT in the allowed set
        page_name = re.sub(r'[^\w\s-]', '', title).strip()
        
        # Step 2: Replace multiple hyphens or spaces with single hyphen
        # "hello   world" or "hello---world" becomes "hello-world"
        page_name = re.sub(r'[-\s]+', '-', page_name).lower()
        
        # Step 3: Add timestamp to ensure uniqueness (avoid name collisions)
        page_name = f"{page_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}.aspx"
        
        # Create page request body
        page_body = {
            "name": page_name,
            "title": title,
            "pageLayout": self.config.page_template.lower()  # article, home, etc.
        }
        
        if description:
            page_body["description"] = description
        
        # Create the page
        url = f"{self._pages_base()}/sites/{self.config.site_id}/pages"
        
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
        Set the content of a SharePoint page using canvas content (Step 2).
        
        MS GRAPH API CALL
        ------------------
        PATCH https://graph.microsoft.com/beta/sites/{siteId}/pages/{pageId}
        
        Request Body:
        {
            "canvasLayout": {
                "horizontalSections": [
                    {
                        "columns": [
                            {
                                "factor": 12,
                                "webparts": [
                                    {"id": "wp-1-abc", "innerHtml": "<h2>Problem</h2>..."}
                                ]
                            }
                        ],
                        "emphasis": "none"
                    }
                ]
            }
        }
        
        Response: 200 OK or 204 No Content
        
        CANVAS LAYOUT STRUCTURE
        ------------------------
        The canvas is SharePoint's page layout engine:
        
        Page Canvas
        ├── horizontalSections[]  ← Rows (bands across the page)
        │   ├── columns[]         ← Columns within each row
        │   │   ├── factor        ← Width (1-12 in a 12-column grid)
        │   │   └── webparts[]    ← Content blocks in this column
        │   │       ├── id        ← Unique web part identifier
        │   │       └── innerHtml ← The actual HTML content
        │   └── emphasis          ← Background color/style
        
        This method uses the MarkdownToSharePointConverter to:
        1. Convert each markdown section to HTML
        2. Wrap HTML in web part structure
        3. Organize web parts into sections
        4. Build the complete canvas layout JSON
        
        Args:
            session: aiohttp session
            page_id: The ID of the page to update (from create_page response)
            sections: Dictionary of section_name -> markdown_content
            title: Page title for conversion context
            
        Returns:
            True if content was set successfully
            
        Raises:
            Exception: If update fails (invalid page_id, permissions, etc.)
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Convert sections to SharePoint canvas format using our converter
        # This transforms: {"Problem": "## Problem\n..."} 
        # Into: {"canvasLayout": {"horizontalSections": [...]}}
        canvas_content = self.converter.convert_document(sections, title)
        
        # Update page content via PATCH request
        url = f"{self._pages_base()}/sites/{self.config.site_id}/pages/{page_id}"
        
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
        Publish a SharePoint page, making it visible to users (Step 3).
        
        DRAFT vs PUBLISHED PAGES
        -------------------------
        When you create a page via Graph API, it starts as a DRAFT.
        Drafts are only visible to editors (people with edit permissions).
        
        Publishing makes the page visible to ALL users with read access.
        
        MS GRAPH API CALL
        ------------------
        POST https://graph.microsoft.com/beta/sites/{siteId}/pages/{pageId}/publish
        
        No request body needed!
        
        Response: 200 OK or 204 No Content
        
        After publishing, we make a GET request to retrieve the final webUrl:
        GET https://graph.microsoft.com/beta/sites/{siteId}/pages/{pageId}
        
        Response includes:
        {
            "webUrl": "https://company.sharepoint.com/sites/site/SitePages/my-doc.aspx",
            "publishingState": "published",
            ...
        }
        
        Args:
            session: aiohttp session
            page_id: The ID of the page to publish (from create_page response)
            
        Returns:
            Published page URL
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Publish the page
        url = f"{self._pages_base()}/sites/{self.config.site_id}/pages/{page_id}/publish"
        
        status, response_text = await self._request_with_retry(
            session, "POST", url, headers
        )
        
        if status in (200, 204):
            logger.info(f"Published page: {page_id}")
        else:
            raise Exception(f"Failed to publish page: {status} - {response_text}")
        
        # Get the page URL
        page_url = f"{self._pages_base()}/sites/{self.config.site_id}/pages/{page_id}"
        
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
        Promote a page as a news article (Optional Step 4).
        
        NEWS vs REGULAR PAGES
        ----------------------
        SharePoint has two ways to display pages:
        
        1. Regular Page: Appears in SitePages library, accessible via direct link
        2. News Post: Also appears in "News" web part on the homepage
        
        News posts get more visibility - they show up in:
        - Site homepage news feed
        - SharePoint Start page
        - Microsoft Teams (if site is linked)
        - Mobile app news feed
        
        MS GRAPH API CALL
        ------------------
        PATCH https://graph.microsoft.com/beta/sites/{siteId}/pages/{pageId}
        
        Request Body:
        {
            "promotionKind": "newsPost"
        }
        
        Other promotionKind options:
        - "page" (default - regular page)
        - "newsPost" (appears in news feed)
        
        Response: 200 OK or 204 No Content
        
        Args:
            session: aiohttp session
            page_id: The ID of the page to promote
            
        Returns:
            True if promotion successful, False if failed (non-fatal)
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        url = f"{self._pages_base()}/sites/{self.config.site_id}/pages/{page_id}"
        
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
            # This is non-fatal - page is still published, just not as news
            logger.warning(f"Failed to promote as news: {status} - {response_text}")
            return False
    
    async def ensure_folder_exists(
        self,
        session: aiohttp.ClientSession,
        folder_path: str
    ) -> bool:
        """
        Ensure target folder exists in Site Pages library.
        
        SHAREPOINT FILE STRUCTURE
        --------------------------
        SharePoint sites have a "SitePages" library where all modern pages live.
        We can create subfolders to organize pages:
        
        SitePages/
        ├── Home.aspx
        ├── About.aspx
        └── Generated Documentation/     ← Our target folder
            ├── architecture-doc-1.aspx
            └── architecture-doc-2.aspx
        
        MS GRAPH API CALLS
        -------------------
        1. Check if folder exists:
           GET /sites/{siteId}/drive/root:/SitePages/{folderPath}
           
           200 OK = folder exists
           404 Not Found = need to create it
        
        2. Create folder if needed:
           POST /sites/{siteId}/drive/root:/SitePages:/children
           
           Request Body:
           {
               "name": "Generated Documentation",
               "folder": {},
               "@microsoft.graph.conflictBehavior": "replace"
           }
        
        Args:
            session: aiohttp session
            folder_path: Target folder name (e.g., "Generated Documentation")
            
        Returns:
            True if folder exists or was created successfully
        """
        token = await self._ensure_valid_token()
        headers = self._get_headers(token)
        
        # Check if folder exists using drive API
        folder_url = f"{self.GRAPH_BASE_URL}/sites/{self.config.site_id}/drive/root:/SitePages/{folder_path}"
        
        status, _ = await self._request_with_retry(
            session, "GET", folder_url, headers
        )
        
        if status == 200:
            return True  # Folder already exists
        
        if status == 404:
            # Create the folder
            create_folder_url = f"{self.GRAPH_BASE_URL}/sites/{self.config.site_id}/drive/root:/SitePages:/children"
            folder_body = {
                "name": folder_path,
                "folder": {},  # Empty object indicates this is a folder, not a file
                "@microsoft.graph.conflictBehavior": "replace"  # Overwrite if exists
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
        
        This is the MAIN ENTRY POINT for the Orchestrator to call.
        It orchestrates the entire publishing process.
        
        COMPLETE PUBLISHING WORKFLOW
        =============================
        
        ┌─────────────────────────────────────────────────────────────────┐
        │                       ORCHESTRATOR                              │
        │    {"Problem": "## Problem\n...", "Solution": "..."}           │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  Step 0: Validate Configuration                                 │
        │  - Check SHAREPOINT_SITE_ID, AZURE_TENANT_ID, etc.             │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  Step 1: Ensure Folder Exists                                   │
        │  GET /sites/{siteId}/drive/root:/SitePages/{folder}            │
        │  POST (if 404)                                                  │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  Step 2: Create Draft Page                                      │
        │  POST /sites/{siteId}/pages                                     │
        │  → Returns page_id                                              │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  Step 3: Set Page Content                                       │
        │  - Convert markdown → HTML                                      │
        │  - Create web parts                                             │
        │  - PATCH /sites/{siteId}/pages/{pageId}                        │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  Step 4: Publish Page                                           │
        │  POST /sites/{siteId}/pages/{pageId}/publish                   │
        │  → Page now visible to all users                                │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼ (optional)
        ┌─────────────────────────────────────────────────────────────────┐
        │  Step 5: Promote as News (if configured)                        │
        │  PATCH /sites/{siteId}/pages/{pageId}                          │
        │  {"promotionKind": "newsPost"}                                  │
        └─────────────────────────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  Return PublishResult                                           │
        │  {success: true, page_url: "...", page_id: "...", ...}         │
        └─────────────────────────────────────────────────────────────────┘
        
        ERROR HANDLING
        ---------------
        - Configuration errors: Return PublishResult with error, don't throw
        - API errors: Caught and returned as PublishResult with error
        - Network errors: Retried 3x with exponential backoff, then return error
        
        Args:
            title: Page title (displayed in SharePoint)
            sections: Dictionary of section_name -> markdown_content
                      Example: {"Problem": "## Problem\n...", "Solution": "..."}
            description: Optional page description (shown in search results)
            diagram_description: Description of the analyzed diagram (added as metadata)
            donor_pattern: ID of the donor pattern used (added as metadata)
            
        Returns:
            PublishResult with:
            - success: True if page was published successfully
            - page_id: SharePoint page ID (for future updates)
            - page_url: Full URL to the published page
            - error: Error message if success=False
            - publish_time_ms: Total time for the operation
        """
        start_time = datetime.now()
        
        # =====================================================================
        # STEP 0: VALIDATE CONFIGURATION
        # =====================================================================
        if not self.config.is_valid():
            return PublishResult(
                success=False,
                error="SharePoint configuration is incomplete. Check SHAREPOINT_SITE_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET."
            )
        
        # =====================================================================
        # ADD METADATA SECTION
        # =====================================================================
        # We add a "Document Metadata" section at the end with:
        # - Source diagram analysis (truncated to 500 chars)
        # - Reference pattern ID
        # - Generation timestamp
        # =====================================================================
        sections_with_metadata = dict(sections)
        if diagram_description or donor_pattern:
            metadata_md = "\n\n---\n\n## Document Metadata\n\n"
            if diagram_description:
                # Truncate long descriptions to keep page clean
                desc_preview = diagram_description[:500]
                if len(diagram_description) > 500:
                    desc_preview += "..."
                metadata_md += f"**Source Diagram Analysis:**\n{desc_preview}\n\n"
            if donor_pattern:
                metadata_md += f"**Reference Pattern:** {donor_pattern}\n\n"
            metadata_md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            sections_with_metadata["Document Metadata"] = metadata_md
        
        # =====================================================================
        # EXECUTE PUBLISHING WORKFLOW
        # =====================================================================
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
