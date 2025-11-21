from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from job_runner.log_store import LogStore
from job_runner.models import JobStatus
from job_runner.storage import JobStore


class JobRunner:
    """Async worker that executes jobs sequentially."""

    def __init__(self, job_store: JobStore, log_store: LogStore) -> None:
        self.job_store = job_store
        self.log_store = log_store
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self.python_bin = sys.executable

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def enqueue(self, job_id: str) -> None:
        await self._queue.put(job_id)

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._run_job(job_id)
            except Exception as exc:  # pragma: no cover - safety net
                await self.log_store.append(job_id, f"Runner crashed: {exc}\n")
            finally:
                self._queue.task_done()

    async def _run_job(self, job_id: str) -> None:
        record = await self.job_store.get(job_id)
        await self.job_store.mark_running(job_id)
        await self.log_store.append(job_id, f"[runner] starting job {job_id}\n")

        paths = record.paths
        spec = record.spec
        entry_path = (paths.code / spec.entry).resolve()
        if not entry_path.is_file():
            await self.log_store.append(
                job_id, f"[runner] entry file not found: {entry_path}\n"
            )
            await self.job_store.mark_finished(
                job_id,
                status=JobStatus.failed,
                exit_code=127,
                error="missing entry file",
            )
            await self.log_store.mark_complete(job_id)
            return

        env = os.environ.copy()
        env.update(spec.env)
        env.setdefault("JOB_ID", job_id)
        env.setdefault("JOB_INPUT_DIR", str(paths.input))
        env.setdefault("JOB_OUTPUT_DIR", str(paths.artifacts))
        cmd = [self.python_bin, entry_path.name, *spec.args]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(paths.code),
                env=env,
            )
        except FileNotFoundError as exc:
            await self.log_store.append(
                job_id, f"[runner] failed to spawn process: {exc}\n"
            )
            await self.job_store.mark_finished(
                job_id, status=JobStatus.failed, exit_code=127, error=str(exc)
            )
            await self.log_store.mark_complete(job_id)
            return

        exit_code = None
        timeout_error = None

        async def consume_output():
            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                await self.log_store.append(job_id, line.decode(errors="replace"))

        reader = asyncio.create_task(consume_output())

        try:
            await asyncio.wait_for(process.wait(), timeout=float(spec.timeout_sec))
            exit_code = process.returncode
        except asyncio.TimeoutError as exc:
            timeout_error = exc
            process.kill()
            await process.wait()
            exit_code = process.returncode
        finally:
            await reader

        if timeout_error:
            await self.log_store.append(
                job_id, "[runner] timeout exceeded, process terminated\n"
            )

        artifacts = self._list_artifacts(paths.artifacts)
        status = (
            JobStatus.succeeded
            if exit_code == 0 and timeout_error is None
            else JobStatus.failed
        )
        error_message = None
        if status is JobStatus.failed:
            error_message = "timeout" if timeout_error else "non-zero exit"
        await self.job_store.mark_finished(
            job_id,
            status=status,
            exit_code=exit_code,
            error=error_message,
            artifacts=artifacts,
        )
        await self.log_store.append(
            job_id, f"[runner] finished with code {exit_code}\n"
        )
        await self.log_store.mark_complete(job_id)

    @staticmethod
    def _list_artifacts(path: Path) -> list[str]:
        if not path.exists():
            return []
        return sorted(p.name for p in path.iterdir() if p.is_file())
