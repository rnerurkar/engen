"""
Workflow State Manager — persists wizard state in AlloyDB for resumable sessions.

Each user session gets a workflow_id. After every phase transition the orchestrator
calls save_state() to snapshot the current step + all accumulated data.  When the
user returns, resume_state() reloads the snapshot so the React app can jump back
to the correct step.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import sqlalchemy
from sqlalchemy import text

logger = logging.getLogger(__name__)


class WorkflowStateManager:
    """CRUD for the workflow_state table."""

    # Valid phase transitions (linear wizard)
    PHASES = ["INPUT", "DOC_REVIEW", "CODE_GEN", "CODE_REVIEW", "PUBLISH", "COMPLETED"]

    def __init__(self, engine: sqlalchemy.Engine):
        """
        Args:
            engine: SQLAlchemy engine (from AlloyDBManager.engine).
        """
        self.engine = engine
        self._ensure_table()

    # ── Bootstrap ─────────────────────────────────────────────────────────

    def _ensure_table(self):
        """Create the workflow_state table if it doesn't exist."""
        ddl = text("""
            CREATE TABLE IF NOT EXISTS workflow_state (
                workflow_id       VARCHAR(64) PRIMARY KEY,
                created_by        VARCHAR(256),
                pattern_title     VARCHAR(512),
                current_phase     VARCHAR(32) NOT NULL DEFAULT 'INPUT',
                image_base64      TEXT,
                doc_data          JSONB,
                hadr_sections     JSONB,
                hadr_diagram_uris JSONB,
                code_data         JSONB,
                doc_review_id     VARCHAR(64),
                code_review_id    VARCHAR(64),
                created_at        TIMESTAMPTZ DEFAULT NOW(),
                last_updated      TIMESTAMPTZ DEFAULT NOW(),
                is_active         BOOLEAN DEFAULT TRUE
            )
        """)
        idx1 = text("""
            CREATE INDEX IF NOT EXISTS idx_workflow_user
            ON workflow_state(created_by, is_active, last_updated DESC)
        """)
        idx2 = text("""
            CREATE INDEX IF NOT EXISTS idx_workflow_active
            ON workflow_state(is_active, last_updated)
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(ddl)
                conn.execute(idx1)
                conn.execute(idx2)
            logger.info("workflow_state table ensured")
        except Exception as e:
            logger.error(f"Failed to create workflow_state table: {e}")

    # ── Create ────────────────────────────────────────────────────────────

    def create_workflow(
        self,
        workflow_id: str,
        pattern_title: str,
        created_by: str = "anonymous",
        image_base64: Optional[str] = None,
    ) -> bool:
        """Create a new workflow record at the INPUT phase."""
        stmt = text("""
            INSERT INTO workflow_state
                (workflow_id, created_by, pattern_title, current_phase, image_base64)
            VALUES
                (:wid, :user, :title, 'INPUT', :img)
            ON CONFLICT (workflow_id) DO NOTHING
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(stmt, {
                    "wid": workflow_id,
                    "user": created_by,
                    "title": pattern_title,
                    "img": image_base64,
                })
            logger.info(f"Created workflow {workflow_id} for '{pattern_title}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create workflow {workflow_id}: {e}")
            return False

    # ── Save (upsert) ────────────────────────────────────────────────────

    def save_state(
        self,
        workflow_id: str,
        current_phase: str,
        **kwargs: Any,
    ) -> bool:
        """
        Save the current workflow state.  Only the fields provided in kwargs
        are updated — others are left untouched.

        Accepted kwargs:
            pattern_title, image_base64, doc_data, hadr_sections,
            hadr_diagram_uris, code_data, doc_review_id, code_review_id
        """
        if current_phase not in self.PHASES:
            logger.error(f"Invalid phase '{current_phase}' for workflow {workflow_id}")
            return False

        # Build dynamic SET clause
        set_parts = ["current_phase = :phase", "last_updated = :now"]
        params: Dict[str, Any] = {
            "wid": workflow_id,
            "phase": current_phase,
            "now": datetime.now(timezone.utc),
        }

        allowed_fields = {
            "pattern_title": "pattern_title",
            "image_base64": "image_base64",
            "doc_data": "doc_data",
            "hadr_sections": "hadr_sections",
            "hadr_diagram_uris": "hadr_diagram_uris",
            "code_data": "code_data",
            "doc_review_id": "doc_review_id",
            "code_review_id": "code_review_id",
        }

        for kwarg_key, col_name in allowed_fields.items():
            if kwarg_key in kwargs:
                value = kwargs[kwarg_key]
                # Serialize dicts/lists to JSON strings for JSONB columns
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                set_parts.append(f"{col_name} = :{kwarg_key}")
                params[kwarg_key] = value

        set_clause = ", ".join(set_parts)
        stmt = text(f"""
            UPDATE workflow_state
            SET {set_clause}
            WHERE workflow_id = :wid AND is_active = TRUE
        """)

        try:
            with self.engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    logger.warning(f"No active workflow found for {workflow_id}")
                    return False
            logger.info(f"Saved workflow {workflow_id} → phase={current_phase}")
            return True
        except Exception as e:
            logger.error(f"Failed to save workflow {workflow_id}: {e}")
            return False

    # ── Resume (load) ────────────────────────────────────────────────────

    def load_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the full workflow state for resuming.

        Returns:
            Dict with all fields, or None if not found / inactive.
        """
        stmt = text("""
            SELECT workflow_id, created_by, pattern_title, current_phase,
                   image_base64, doc_data, hadr_sections, hadr_diagram_uris,
                   code_data, doc_review_id, code_review_id,
                   created_at, last_updated
            FROM workflow_state
            WHERE workflow_id = :wid AND is_active = TRUE
        """)
        try:
            with self.engine.begin() as conn:
                row = conn.execute(stmt, {"wid": workflow_id}).mappings().first()
            if not row:
                return None

            state = dict(row)
            # Parse JSONB fields back to Python dicts
            for json_field in ("doc_data", "hadr_sections", "hadr_diagram_uris", "code_data"):
                if state.get(json_field) and isinstance(state[json_field], str):
                    state[json_field] = json.loads(state[json_field])

            # Convert timestamps to ISO strings for JSON serialisation
            for ts_field in ("created_at", "last_updated"):
                if state.get(ts_field):
                    state[ts_field] = state[ts_field].isoformat()

            return state
        except Exception as e:
            logger.error(f"Failed to load workflow {workflow_id}: {e}")
            return None

    # ── List active workflows for a user ──────────────────────────────────

    def list_active_workflows(
        self,
        created_by: str,
        limit: int = 10,
    ) -> list:
        """
        List recent active workflows for a user (for a "Resume" picker UI).

        Returns:
            List of dicts with workflow_id, pattern_title, current_phase, last_updated.
        """
        stmt = text("""
            SELECT workflow_id, pattern_title, current_phase, last_updated
            FROM workflow_state
            WHERE created_by = :user AND is_active = TRUE
            ORDER BY last_updated DESC
            LIMIT :lim
        """)
        try:
            with self.engine.begin() as conn:
                rows = conn.execute(stmt, {"user": created_by, "lim": limit}).mappings().all()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list workflows for {created_by}: {e}")
            return []

    # ── Deactivate (soft delete) ──────────────────────────────────────────

    def deactivate_workflow(self, workflow_id: str) -> bool:
        """Soft-delete a workflow (e.g., after successful publish or user reset)."""
        stmt = text("""
            UPDATE workflow_state
            SET is_active = FALSE, last_updated = :now
            WHERE workflow_id = :wid
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(stmt, {
                    "wid": workflow_id,
                    "now": datetime.now(timezone.utc),
                })
            logger.info(f"Deactivated workflow {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate workflow {workflow_id}: {e}")
            return False
