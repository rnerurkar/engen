import os
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass


class Config:
    """Configuration with validation for all required environment variables"""
    
    # Required environment variables
    REQUIRED_VARS = [
        'GCP_PROJECT_ID',
        'GCS_IMAGE_BUCKET',
        'VERTEX_SEARCH_DS_ID',
        'VERTEX_VECTOR_ENDPOINT_ID',
        'VERTEX_DEPLOYED_INDEX_ID',
        'AZURE_TENANT_ID',
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET',
        'SP_SITE_ID',
        'SP_LIST_ID'
    ]
    
    def __init__(self):
        # GCP
        self.PROJECT_ID = os.getenv("GCP_PROJECT_ID")
        self.LOCATION = os.getenv("GCP_LOCATION", "us-central1")
        self.GCS_BUCKET = os.getenv("GCS_IMAGE_BUCKET")
        
        # Vertex AI
        self.SEARCH_DATA_STORE_ID = os.getenv("VERTEX_SEARCH_DS_ID")
        self.VECTOR_INDEX_ENDPOINT = os.getenv("VERTEX_VECTOR_ENDPOINT_ID")
        self.DEPLOYED_INDEX_ID = os.getenv("VERTEX_DEPLOYED_INDEX_ID")
        
        # Firestore
        self.FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "patterns")
        
        # SharePoint (Azure AD App)
        self.AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
        self.AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
        self.AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
        self.SP_SITE_ID = os.getenv("SP_SITE_ID")
        self.SP_LIST_ID = os.getenv("SP_LIST_ID")
        self.SP_PAGES_LIBRARY = os.getenv("SP_PAGES_LIBRARY", "SitePages")
        
        # Validate configuration
        self._validate()
    
    def _validate(self):
        """Validate that all required environment variables are set"""
        missing = []
        for var in self.REQUIRED_VARS:
            env_value = os.getenv(var)
            if not env_value:
                missing.append(var)
        
        if missing:
            error_msg = f"Missing required environment variables: {', '.join(missing)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        logger.info(f"Configuration validated: {len(self.REQUIRED_VARS)} required variables loaded")
