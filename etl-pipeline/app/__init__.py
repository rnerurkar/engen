# app/__init__.py

# Expose key classes for easier importing
# This allows you to do: "from app import MSGraphClient, ContentProcessor"
# Instead of: "from app.sp_client import MSGraphClient"

from .sp_client import MSGraphClient
from .processor import ContentProcessor
from .chunker import SemanticChunker
from .ingestor import VertexIngestor

# Version of the ETL package
__version__ = "1.0.0"

# Set up a default logging handler to avoid "No handler found" warnings
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())