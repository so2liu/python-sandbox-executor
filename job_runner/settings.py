from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    use_fake_redis: bool = field(
        default_factory=lambda: os.getenv("FAKE_REDIS", "0") == "1"
    )
    job_data_dir: str = field(
        default_factory=lambda: os.getenv("JOB_DATA_DIR", "data/jobs")
    )
    inline_worker: bool = field(
        default_factory=lambda: os.getenv("INLINE_WORKER", "1") == "1"
    )
    queue_key: str = field(
        default_factory=lambda: os.getenv("JOB_QUEUE_KEY", "jobs:queue")
    )
    use_docker: bool = field(
        default_factory=lambda: os.getenv("USE_DOCKER", "1") == "1"
    )
    docker_image: str = field(
        default_factory=lambda: os.getenv("JOB_RUN_IMAGE", "job-runner-exec:py3.12")
    )
    docker_bin: str = field(default_factory=lambda: os.getenv("DOCKER_BIN", "docker"))
    static_dir: str = field(default_factory=lambda: os.getenv("STATIC_DIR", "static"))


def get_settings() -> Settings:
    return Settings()
