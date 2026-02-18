from config import Config
import logging
import json
import sqlalchemy
from sqlalchemy import create_engine, text
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CloudSQLManager:
    """
    Manages interactions with a CloudSQL (PostgreSQL) instance for persistent review tracking and publishing status.
    Schema expected:
    CREATE TABLE reviews (
        review_id VARCHAR(36) PRIMARY KEY,
        title TEXT,
        stage VARCHAR(50), -- 'PATTERN' or 'ARTIFACT'
        status VARCHAR(50), -- 'PENDING', 'APPROVED', 'REJECTED'
        artifacts_json JSONB,
        documentation TEXT,
        feedback TEXT,
        doc_publish_status VARCHAR(50), -- 'NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
        code_publish_status VARCHAR(50), -- 'NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
        doc_url TEXT,
        code_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    def __init__(self, connection_name: str, db_user: str, db_pass: str, db_name: str):
        # Construct the connection string
        # For production (Cloud Run/App Engine), use the unix socket path
        # For local (with proxy), use 127.0.0.1
        
        # Adjust based on environment execution context
        self.db_uri = f"postgresql+pg8000://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}"
        
        db_config = {
            "pool_size": 5,
            "max_overflow": 2,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
        
        try:
            self.engine = create_engine(self.db_uri, **db_config)
            logger.info("CloudSQL Engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize CloudSQL Engine: {e}")
            self.engine = None

    def create_review_record(self, review_id: str, title: str, stage: str, artifacts: Dict, doc: str):
        if not self.engine:
            logger.warning("DB Engine not available. Skipping persistent record creation.")
            return

        # Ensure schema supports new columns. If not, this might fail unless we handles schema migration.
        # For now, we assume schema is up to date.
        stmt = text("""
            INSERT INTO reviews (review_id, title, stage, status, artifacts_json, documentation, doc_publish_status, code_publish_status)
            VALUES (:rid, :title, :stage, 'PENDING', :artifacts, :doc, 'NOT_STARTED', 'NOT_STARTED')
            ON CONFLICT (review_id) DO UPDATE 
            SET title = EXCLUDED.title, artifacts_json = EXCLUDED.artifacts_json, documentation = EXCLUDED.documentation, updated_at = NOW();
        """)
        
        try:
            with self.engine.begin() as conn: # Use begin() for transaction
                conn.execute(stmt, {
                    "rid": review_id,
                    "title": title,
                    "stage": stage,
                    "artifacts": json.dumps(artifacts),
                    "doc": doc
                })
        except Exception as e:
            logger.error(f"Failed to create review record: {e}")

    def update_review_status(self, review_id: str, status: str, feedback: str):
         if not self.engine: return
         stmt = text("UPDATE reviews SET status=:status, feedback=:feedback, updated_at=NOW() WHERE review_id=:rid")
         with self.engine.connect() as conn:
             conn.execute(stmt, {"status": status, "feedback": feedback, "rid": review_id})
             conn.commit()

    def update_publishing_status(self, review_id: str, publish_type: str, status: str, url: str = None):
        """
        Updates the publishing status for documentation or code.
        publish_type: 'doc' or 'code'
        """
        if not self.engine: return
        
        col_status = "doc_publish_status" if publish_type == "doc" else "code_publish_status"
        col_url = "doc_url" if publish_type == "doc" else "code_url"
        
        stmt = text(f"UPDATE reviews SET {col_status}=:status, {col_url}=:url, updated_at=NOW() WHERE review_id=:rid")
        
        with self.engine.connect() as conn:
            conn.execute(stmt, {"status": status, "url": url, "rid": review_id})
            conn.commit()
