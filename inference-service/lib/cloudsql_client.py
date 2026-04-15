"""
AlloyDB Manager — persistent review tracking and publishing status.

Replaces the previous CloudSQLManager.  AlloyDB is wire-compatible with
PostgreSQL so all DDL, JSONB columns, indexes and SQL queries work unchanged.
Only the connection layer differs: we use the AlloyDB Auth Proxy connector
(`google-cloud-alloydb-connector`) instead of the Cloud SQL connector.

For backward compatibility the class is aliased as CloudSQLManager so existing
imports continue to work without modification during the migration period.
"""

from config import Config
import logging
import json
import os
import sqlalchemy
from sqlalchemy import create_engine, text
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connector selection — prefer AlloyDB connector, fall back to direct URI
# ---------------------------------------------------------------------------
_USE_ALLOYDB_CONNECTOR = True
try:
    from google.cloud.alloydb.connector import Connector as AlloyDBConnector
except ImportError:
    logger.warning(
        "google-cloud-alloydb-connector not installed — falling back to direct "
        "pg8000 connection.  Install with: pip install google-cloud-alloydb-connector[pg8000]"
    )
    _USE_ALLOYDB_CONNECTOR = False


class AlloyDBManager:
    """
    Manages interactions with an AlloyDB (PostgreSQL-compatible) instance for
    persistent review tracking and publishing status.

    Connection modes:
      • **AlloyDB Auth Proxy** (production): Uses ``google-cloud-alloydb-connector``
        with ``connection_name`` in the format
        ``projects/<PROJECT>/locations/<REGION>/clusters/<CLUSTER>/instances/<INSTANCE>``.
      • **Direct TCP** (local dev): Falls back to a plain ``pg8000`` connection
        string when the connector library is not available.

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
        """
        Args:
            connection_name: AlloyDB instance URI
                Format: projects/<PROJECT>/locations/<REGION>/clusters/<CLUSTER>/instances/<INSTANCE>
                (For local dev without the connector, this value is ignored and a direct
                TCP connection to 127.0.0.1:5432 is used instead.)
            db_user: Database username.
            db_pass: Database password.
            db_name: Database name.
        """
        self.connection_name = connection_name

        db_config = {
            "pool_size": 5,
            "max_overflow": 2,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }

        try:
            if _USE_ALLOYDB_CONNECTOR:
                connector = AlloyDBConnector()

                def _getconn():
                    return connector.connect(
                        connection_name,
                        "pg8000",
                        user=db_user,
                        password=db_pass,
                        db=db_name,
                    )

                self.engine = create_engine(
                    "postgresql+pg8000://",
                    creator=_getconn,
                    **db_config,
                )
            else:
                # Local dev fallback — direct TCP via AlloyDB Auth Proxy sidecar
                db_uri = f"postgresql+pg8000://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}"
                self.engine = create_engine(db_uri, **db_config)

            logger.info("AlloyDB engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize AlloyDB engine: {e}")
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


# ---------------------------------------------------------------------------
# Backward-compatibility alias — existing imports of CloudSQLManager continue
# to work without modification during the migration period.
# ---------------------------------------------------------------------------
CloudSQLManager = AlloyDBManager
