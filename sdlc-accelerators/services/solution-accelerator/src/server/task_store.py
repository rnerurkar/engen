"""Async MCP Task store. In-memory reference; AlloyDB-backed in production (TODO).
Implements the queued->running->completed/failed lifecycle with 24h retention semantics.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["queued", "running", "completed", "failed"]


@dataclass
class Task:
    task_id: str
    status: Status = "queued"
    stage: str = ""
    result: Any = None
    error: str | None = None
    owner_id: str = ""
    created_at: float = field(default_factory=time.time)


class TaskStore:
    """TODO(live): back with AlloyDB + row-level security + 24h retention."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create(self, owner_id: str = "") -> Task:
        t = Task(task_id=str(uuid.uuid4()), owner_id=owner_id)
        self._tasks[t.task_id] = t
        return t

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs: Any) -> Task:
        t = self._tasks[task_id]
        for k, v in kwargs.items():
            setattr(t, k, v)
        return t
