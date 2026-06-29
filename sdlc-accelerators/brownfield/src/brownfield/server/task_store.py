"""Brownfield task store — async MCP task records, owner_id-isolated, 24h retention (live: AlloyDB)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    task_id: str
    owner_id: str
    status: str = "queued"  # queued | running | completed | failed
    stage: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: float = field(default_factory=time.time)


class TaskStore:
    """Reference backing. Production: AlloyDB with Row-Level Security by owner_id, 24h TTL."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create(self, owner_id: str) -> Task:
        t = Task(task_id=str(uuid.uuid4()), owner_id=owner_id)
        self._tasks[t.task_id] = t
        return t

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs: Any) -> None:
        t = self._tasks.get(task_id)
        if t:
            for k, v in kwargs.items():
                setattr(t, k, v)
