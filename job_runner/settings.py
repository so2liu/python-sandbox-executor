from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    job_data_dir: str = field(
        default_factory=lambda: os.getenv("JOB_DATA_DIR", "data/jobs")
    )
    static_dir: str = field(default_factory=lambda: os.getenv("STATIC_DIR", "static"))


def get_settings() -> Settings:
    return Settings()
