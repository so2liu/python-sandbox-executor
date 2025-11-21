from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    use_fake_redis: bool = os.getenv("FAKE_REDIS", "0") == "1"
    job_data_dir: str = os.getenv("JOB_DATA_DIR", "data/jobs")
    inline_worker: bool = os.getenv("INLINE_WORKER", "1") == "1"
    queue_key: str = os.getenv("JOB_QUEUE_KEY", "jobs:queue")
    use_docker: bool = os.getenv("USE_DOCKER", "1") == "1"
    docker_image: str = os.getenv("JOB_RUN_IMAGE", "job-runner-exec:py3.12")
    docker_bin: str = os.getenv("DOCKER_BIN", "docker")


def get_settings() -> Settings:
    return Settings()
