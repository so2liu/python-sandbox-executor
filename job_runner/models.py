from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JobSpec(BaseModel):
    entry: str = Field(default="main.py")
    args: list[str] = Field(default_factory=list)
    timeout_sec: int = Field(default=60, gt=0, le=600)
    env: dict[str, str] = Field(default_factory=dict)


class JobPaths(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    code: Path
    input: Path
    artifacts: Path


class JobResult(BaseModel):
    job_id: str
    status: Literal["succeeded", "failed"]
    exit_code: int | None = None
    error: str | None = None
    logs: str = ""
    artifacts: list[str] = Field(default_factory=list)
