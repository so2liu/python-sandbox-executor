from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Root directory for job data (per-job subdirs)."""
    root = Path(os.getenv("JOB_DATA_DIR", "data/jobs")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root
