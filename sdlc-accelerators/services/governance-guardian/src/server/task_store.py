"""Async task store for Governance Guardian assess lifecycle (mirrors SA Task Store).
In-memory reference; AlloyDB-backed in production (TODO). owner_id tenant isolation."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["queued", "running", "completed", "failed"]


@dataclass
class AssessTask:
    task_id: str
    status: Status = "queued"
    stage: str = ""
    result: Any = None
    error: str | None = None
    owner_id: str = ""
    created_at: float = field(default_factory=time.time)


class AssessTaskStore:
    def __init__(self):
        self._tasks: dict[str, AssessTask] = {}

    def create(self, owner_id: str = "") -> AssessTask:
        t = AssessTask(task_id=str(uuid.uuid4()), owner_id=owner_id)
        self._tasks[t.task_id] = t
        return t

    def get(self, task_id: str) -> AssessTask | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **kw) -> AssessTask:
        t = self._tasks[task_id]
        for k, v in kw.items():
            setattr(t, k, v)
        return t
