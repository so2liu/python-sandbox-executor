from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from job_runner import config
from job_runner.job_store import JobStore
from job_runner.log_store import LogStore
from job_runner.memory_store import InMemoryJobStore, InMemoryLogStore
from job_runner.models import (
    JobCreateResponse,
    JobPaths,
    JobRecord,
    JobSpec,
    JobStatus,
    JobStatusResponse,
    JobSyncResponse,
    JobView,
)
from job_runner.runner import JobRunner
from job_runner.settings import get_settings
from job_runner.static_utils import prepare_static_dir


settings = get_settings()
if settings.use_fake_redis:
    job_store = InMemoryJobStore()
    log_store = InMemoryLogStore()
    runner = JobRunner(job_store, log_store, redis_client=None)
else:
    job_store = JobStore()
    log_store = LogStore()
    runner = JobRunner(job_store, log_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.inline_worker:
        await runner.start()
    yield


app = FastAPI(title="Job Runner", version="0.1.0", lifespan=lifespan)
static_path = prepare_static_dir()
app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")


def _job_paths(job_id: str) -> JobPaths:
    root = config.data_dir() / job_id
    code_dir = root / "code"
    input_dir = root / "input"
    artifacts_dir = root / "artifacts"
    for d in (code_dir, input_dir, artifacts_dir):
        d.mkdir(parents=True, exist_ok=True)
    return JobPaths(
        root=root,
        code=code_dir,
        input=input_dir,
        artifacts=artifacts_dir,
        log_file=root / "logs.txt",
    )


def _to_view(record: JobRecord) -> JobView:
    return JobView.model_validate(record.model_dump(exclude={"paths"}))


async def _save_files(target: Path, uploads: list[UploadFile]) -> list[str]:
    saved: list[str] = []
    for upload in uploads:
        if not upload.filename:
            continue
        name = Path(upload.filename).name
        data = await upload.read()
        dest = target / name
        dest.write_bytes(data)
        saved.append(name)
    return saved


@app.post("/jobs", response_model=JobCreateResponse)
async def create_job(
    spec: Annotated[str, Form(...)],
    code_files: Annotated[list[UploadFile] | None, File()] = None,
    input_files: Annotated[list[UploadFile] | None, File()] = None,
) -> JobCreateResponse:
    try:
        job_spec = JobSpec.model_validate_json(spec)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"spec is not valid JSON: {exc}"
        ) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    job_id = uuid4().hex
    paths = _job_paths(job_id)
    await log_store.register(job_id)
    code_files = code_files or []
    input_files = input_files or []
    await _save_files(paths.code, code_files)
    await _save_files(paths.input, input_files)

    await job_store.create(job_id, job_spec, paths)
    await runner.enqueue(job_id)
    return JobCreateResponse(job_id=job_id, status=JobStatus.queued)


@app.post("/jobs/sync", response_model=JobSyncResponse)
async def create_job_sync(
    spec: Annotated[str, Form(...)],
    code_files: Annotated[list[UploadFile] | None, File()] = None,
    input_files: Annotated[list[UploadFile] | None, File()] = None,
) -> JobSyncResponse:
    try:
        job_spec = JobSpec.model_validate_json(spec)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"spec is not valid JSON: {exc}"
        ) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    job_id = uuid4().hex
    paths = _job_paths(job_id)
    await log_store.register(job_id)
    code_files = code_files or []
    input_files = input_files or []
    await _save_files(paths.code, code_files)
    await _save_files(paths.input, input_files)

    await job_store.create(job_id, job_spec, paths)
    await runner.enqueue(job_id)

    deadline = asyncio.get_event_loop().time() + job_spec.timeout_sec + 5
    record_view: JobView | None = None
    while True:
        try:
            rec_full = await job_store.get(job_id)
            record_view = _to_view(rec_full)
            if record_view.status in {
                JobStatus.succeeded,
                JobStatus.failed,
                JobStatus.canceled,
            }:
                break
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        if asyncio.get_event_loop().time() > deadline:
            raise HTTPException(
                status_code=504, detail="job did not finish before timeout"
            )
        await asyncio.sleep(0.1)

    lines = await log_store.tail(job_id)
    return JobSyncResponse(
        job=record_view,
        logs="".join(lines),
        artifacts=record_view.artifacts if record_view else [],
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    try:
        record = await job_store.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    lines = await log_store.tail(job_id)
    return JobStatusResponse(job=_to_view(record), log_lines=len(lines))


@app.get("/jobs/{job_id}/logs")
async def full_log(job_id: str) -> PlainTextResponse:
    try:
        await job_store.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    lines = await log_store.tail(job_id)
    body = "".join(lines)
    return PlainTextResponse(body)


@app.get("/jobs/{job_id}/logs/stream")
async def stream_logs(job_id: str) -> StreamingResponse:
    try:
        await job_store.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")

    async def event_source():
        async for line in log_store.stream(job_id):
            text = line.rstrip("\n")
            yield f"data: {text}\n\n"
        yield "event: end\ndata: complete\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.get("/jobs/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str):
    try:
        record = await job_store.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found")
    path = record.paths.artifacts / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path)
