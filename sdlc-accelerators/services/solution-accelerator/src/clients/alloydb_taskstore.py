"""AlloyDB client — durable backing for the async task stores and the GCS-pointer tables.

The platform's in-memory stores (server/task_store.py, artifact_store, findings_store) are
reference implementations. In production they are backed by AlloyDB with Row-Level Security
(owner_id isolation) and 24h retention. This client provides the connection + query interface;
the actual AlloyDB calls are written below but COMMENTED OUT.

INTERFACE + query construction are real; an injectable `_execute` seam makes it testable.
Per root CLAUDE.md, all external calls go through clients/base.with_retry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import with_retry

# Schema the live store expects (created once via migration). Documented here so the wiring is concrete.
SCHEMA_DDL = """
-- Task records (queued->running->completed/failed), 24h retention, RLS by owner_id.
CREATE TABLE IF NOT EXISTS tasks (
    task_id    TEXT PRIMARY KEY,
    owner_id   TEXT NOT NULL,
    status     TEXT NOT NULL,
    stage      TEXT,
    result     JSONB,
    error      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Blueprint artifact pointers (artifacts live in GCS; this row points to them).
CREATE TABLE IF NOT EXISTS blueprint_pointers (
    task_id    TEXT PRIMARY KEY,
    owner_id   TEXT NOT NULL,
    gcs_prefix TEXT NOT NULL,
    manifest   JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Findings pointers (findings.md lives in GCS; this row points to it).
CREATE TABLE IF NOT EXISTS findings_pointers (
    task_id      TEXT PRIMARY KEY,
    owner_id     TEXT NOT NULL,
    gcs_uri      TEXT NOT NULL,
    has_blocking BOOLEAN NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Row-Level Security: a connection may only see rows for its authenticated owner_id.
-- ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;  (+ policy USING (owner_id = current_setting('app.owner_id')))
"""


class AlloydbTaskstoreClient:
    def __init__(
        self,
        instance_uri: str | None = None,
        database: str = "sdlc_accelerators",
        _execute: Callable[[str, tuple[Any, ...]], Any] | None = None,
    ) -> None:
        self.instance_uri = instance_uri
        self.database = database
        self._execute = _execute  # test seam: (sql, params) -> rows

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        """Run a query. Uses the injected _execute in tests; otherwise the live call (commented out)."""
        if self._execute is not None:
            return with_retry(lambda: self._execute(sql, params))  # type: ignore[misc]  # guarded non-None; mypy can't narrow self.attr into a closure
        return self._live_execute(sql, params)

    def _live_execute(self, sql: str, params: tuple[Any, ...]) -> Any:
        """The actual AlloyDB call. COMMENTED OUT until wired.

        TO WIRE (checklist):
          1. `pip install google-cloud-alloydb-connector[pg8000] sqlalchemy` (AlloyDB Python
             connector + driver).
          2. Supply self.instance_uri (projects/<p>/locations/<r>/clusters/<c>/instances/<i>)
             and the database name; run SCHEMA_DDL once as a migration.
          3. Credentials: ADC with the AlloyDB Client role; set RLS owner_id per connection
             (SET app.owner_id = <authenticated sub>) so tenant isolation is enforced in the DB.
          4. Ensure egress to the AlloyDB instance (private IP / VPC connector from Cloud Run).
          5. Uncomment the body and wrap the execute in with_retry(...).
        """
        # from google.cloud.alloydb.connector import Connector
        # import sqlalchemy
        #
        # connector = Connector()
        # def getconn():
        #     return connector.connect(self.instance_uri, "pg8000", db=self.database, enable_iam_auth=True)
        # engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)
        # with engine.connect() as conn:
        #     result = conn.execute(sqlalchemy.text(sql), params)
        #     conn.commit()
        #     return result.fetchall() if result.returns_rows else None
        raise NotImplementedError(
            "AlloyDB live call is written but commented out in _live_execute. "
            "Uncomment it (+ alloydb connector + instance_uri + RLS owner_id), or inject _execute in tests."
        )
