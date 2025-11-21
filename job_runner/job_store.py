from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import redis.asyncio as redis

from job_runner.models import JobPaths, JobRecord, JobSpec, JobStatus
from job_runner.redis_client import get_redis


class JobStore:
    """Redis-backed job metadata store."""

    def __init__(self, client: redis.Redis | None = None) -> None:
        self.redis = client or get_redis()
        self.key_prefix = "job:"

    def _key(self, job_id: str) -> str:
        return f"{self.key_prefix}{job_id}"

    async def create(self, job_id: str, spec: JobSpec, paths: JobPaths) -> JobRecord:
        record = JobRecord(
            id=job_id,
            spec=spec,
            status=JobStatus.queued,
            created_at=self._now(),
            paths=paths,
        )
        await self.redis.set(self._key(job_id), record.model_dump_json())
        return record

    async def get(self, job_id: str) -> JobRecord:
        raw = await self.redis.get(self._key(job_id))
        if raw is None:
            raise KeyError(job_id)
        return JobRecord.model_validate_json(raw)

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
        record = await self.get(job_id)
        record = record.model_copy(update=kwargs)
        await self.redis.set(self._key(job_id), record.model_dump_json())
        return record

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
