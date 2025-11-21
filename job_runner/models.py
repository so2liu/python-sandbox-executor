from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class JobSpec(BaseModel):
    runtime: str = Field(default="python3.12")
    entry: str = Field(default="main.py")
    args: list[str] = Field(default_factory=list)
    timeout_sec: int = Field(default=60, gt=0, le=600)
    cpu_limit: float = Field(default=1.0, gt=0)
    mem_limit_mb: int = Field(default=512, gt=32)
    pids_limit: int = Field(default=128, gt=0)
    net_policy: Literal["none", "outbound"] = Field(default="none")
    env: dict[str, str] = Field(default_factory=dict)


class JobPaths(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    code: Path
    input: Path
    artifacts: Path
    log_file: Path


class JobRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    spec: JobSpec
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    paths: JobPaths


class JobView(BaseModel):
    """Public-facing job info without internal paths."""

    id: str
    spec: JobSpec
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None
    artifacts: list[str] = Field(default_factory=list)


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job: JobView
    log_lines: int
