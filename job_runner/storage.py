from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Iterable

from job_runner.models import JobPaths, JobRecord, JobSpec, JobStatus


class JobStore:
    """In-memory job metadata store."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, job_id: str, spec: JobSpec, paths: JobPaths) -> JobRecord:
        record = JobRecord(
            id=job_id,
            spec=spec,
            status=JobStatus.queued,
            created_at=datetime.now(timezone.utc),
            paths=paths,
        )
        async with self._lock:
            self._jobs[job_id] = record
        return record

    async def all(self) -> list[JobRecord]:
        async with self._lock:
            return list(self._jobs.values())

    async def get(self, job_id: str) -> JobRecord:
        async with self._lock:
            record = self._jobs.get(job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    async def mark_running(self, job_id: str) -> JobRecord:
        return await self._update(
            job_id, status=JobStatus.running, started_at=self._now()
        )

    async def mark_finished(
        self,
        job_id: str,
        status: JobStatus,
        exit_code: int | None,
        error: str | None = None,
        artifacts: Iterable[str] | None = None,
    ) -> JobRecord:
        updates = {
            "status": status,
            "finished_at": self._now(),
            "exit_code": exit_code,
            "error": error,
        }
        if artifacts is not None:
            updates["artifacts"] = list(artifacts)
        return await self._update(job_id, **updates)

    async def update_artifacts(
        self, job_id: str, artifacts: Iterable[str]
    ) -> JobRecord:
        return await self._update(job_id, artifacts=list(artifacts))

    async def _update(self, job_id: str, **kwargs) -> JobRecord:
        async with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise KeyError(job_id)
            record = record.model_copy(update=kwargs)
            self._jobs[job_id] = record
            return record

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
