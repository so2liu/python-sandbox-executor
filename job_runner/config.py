from __future__ import annotations

from pathlib import Path

from job_runner.settings import get_settings


def data_dir() -> Path:
    """Root directory for job data (per-job subdirs)."""
    root = Path(get_settings().job_data_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root
