from __future__ import annotations

import shutil
from pathlib import Path

from job_runner.settings import get_settings


def prepare_static_dir(target: Path | None = None) -> Path:
    """Ensure a static directory exists and is populated with docs/examples."""
    settings = get_settings()
    root = Path(__file__).resolve().parent.parent
    dest = Path(target or settings.static_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    for name in ("README.md", "docker-compose.yml"):
        src = root / name
        if src.exists():
            shutil.copy2(src, dest / name)

    for folder in ("examples", "docs"):
        src = root / folder
        dst = dest / folder
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)

    index_path = dest / "index.html"
    if not index_path.exists():
        index_path.write_text(
            """<!doctype html>
<html><head><meta charset="utf-8"><title>Job Runner Docs</title></head>
<body>
  <h1>Job Runner Offline Docs</h1>
  <ul>
    <li><a href="./README.md">README.md</a></li>
    <li><a href="./docker-compose.yml">docker-compose.yml</a></li>
    <li><a href="./examples/client.html">Example client</a></li>
  </ul>
</body></html>
""",
            encoding="utf-8",
        )
    return dest
