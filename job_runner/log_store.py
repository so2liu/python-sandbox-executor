from __future__ import annotations

import asyncio
from pathlib import Path


class LogStore:
    """Stores logs per job in memory + on disk, supports streaming."""

    def __init__(self) -> None:
        self._logs: dict[str, list[str]] = {}
        self._paths: dict[str, Path] = {}
        self._conditions: dict[str, asyncio.Condition] = {}
        self._closed: set[str] = set()
        self._lock = asyncio.Lock()

    async def register(self, job_id: str, log_path: Path) -> None:
        async with self._lock:
            self._logs.setdefault(job_id, [])
            self._paths[job_id] = log_path
            self._conditions.setdefault(job_id, asyncio.Condition())
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.touch(exist_ok=True)

    async def append(self, job_id: str, text: str) -> None:
        """Append a log line, persist to disk, and wake streamers."""
        async with self._lock:
            self._logs.setdefault(job_id, []).append(text)
            path = self._paths.get(job_id)
            if path:
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(text)
            cond = self._conditions.get(job_id)
        if cond:
            async with cond:
                cond.notify_all()

    async def mark_complete(self, job_id: str) -> None:
        async with self._lock:
            self._closed.add(job_id)
            cond = self._conditions.get(job_id)
        if cond:
            async with cond:
                cond.notify_all()

    async def tail(self, job_id: str) -> list[str]:
        async with self._lock:
            return list(self._logs.get(job_id, []))

    async def stream(self, job_id: str, start_at: int = 0):
        """Async generator yielding logs as they arrive."""
        cond: asyncio.Condition | None
        while True:
            async with self._lock:
                buffer = self._logs.get(job_id, [])
                cond = self._conditions.get(job_id)
                closed = job_id in self._closed
            while start_at < len(buffer):
                yield buffer[start_at]
                start_at += 1
            if closed:
                return
            if cond is None:
                return
            async with cond:
                await cond.wait()
