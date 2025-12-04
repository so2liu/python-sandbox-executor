from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from job_runner.models import JobPaths, JobResult, JobSpec


async def run_code(job_id: str, paths: JobPaths, spec: JobSpec) -> JobResult:
    """Execute code and return result."""
    logs: list[str] = []

    entry_path = (paths.code / spec.entry).resolve()
    if not entry_path.is_file():
        return JobResult(
            job_id=job_id,
            status="failed",
            exit_code=127,
            error="missing entry file",
            logs=f"[runner] entry file not found: {entry_path}\n",
        )

    env = os.environ.copy()
    env.update(spec.env)
    env.setdefault("JOB_ID", job_id)
    env.setdefault("JOB_INPUT_DIR", str(paths.input))
    env.setdefault("JOB_OUTPUT_DIR", str(paths.artifacts))
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

    cmd = [sys.executable, entry_path.name, *spec.args]
    cwd = str(paths.code)

    logs.append(f"[runner] starting job {job_id}\n")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )
    except FileNotFoundError as exc:
        logs.append(f"[runner] failed to spawn process: {exc}\n")
        return JobResult(
            job_id=job_id,
            status="failed",
            exit_code=127,
            error=str(exc),
            logs="".join(logs),
        )

    exit_code = None
    timeout_error = None

    async def consume_output():
        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            logs.append(line.decode(errors="replace"))

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
        logs.append("[runner] timeout exceeded, process terminated\n")

    artifacts = _list_artifacts(paths.artifacts)
    status = "succeeded" if exit_code == 0 and timeout_error is None else "failed"
    error_message = None
    if status == "failed":
        error_message = "timeout" if timeout_error else "non-zero exit"

    logs.append(f"[runner] finished with code {exit_code}\n")

    return JobResult(
        job_id=job_id,
        status=status,
        exit_code=exit_code,
        error=error_message,
        logs="".join(logs),
        artifacts=artifacts,
    )


def _list_artifacts(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(p.name for p in path.iterdir() if p.is_file())
