from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from job_runner import config
from job_runner import mpl_config as _  # noqa: F401 - configure matplotlib CJK fonts
from job_runner.models import JobPaths, JobResult, JobSpec
from job_runner.runner import run_code
from job_runner.static_utils import prepare_static_dir

API_DESCRIPTION = """
Python Code Runner - Execute Python code and download artifacts.

## How to Output Downloadable Artifacts

Your code can output files that will be available for download.
Use the `JOB_OUTPUT_DIR` environment variable to get the output directory path:

```python
import os

output_dir = os.environ["JOB_OUTPUT_DIR"]

# Save any file to this directory
with open(os.path.join(output_dir, "result.txt"), "w") as f:
    f.write("Hello!")

# Save Excel with pandas
import pandas as pd
df = pd.DataFrame({"a": [1, 2, 3]})
df.to_excel(os.path.join(output_dir, "data.xlsx"), index=False)

# Save image with matplotlib
import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
plt.savefig(os.path.join(output_dir, "chart.png"))
```

All files saved to `JOB_OUTPUT_DIR` will appear in the `artifacts` list of the response,
and can be downloaded via `GET /jobs/{job_id}/artifacts/{filename}`.

## Environment Variables Available in Your Code

- `JOB_ID` - Unique job identifier
- `JOB_INPUT_DIR` - Directory containing uploaded input files
- `JOB_OUTPUT_DIR` - Directory for output artifacts (files here can be downloaded)
"""

app = FastAPI(
    title="Python Code Runner",
    version="0.1.0",
    description=API_DESCRIPTION,
)
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
    )


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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index():
    return FileResponse(static_path / "index.html")


@app.post("/run", response_model=JobResult)
async def run(
    spec: Annotated[str, Form(...)],
    code_files: Annotated[list[UploadFile] | None, File()] = None,
    input_files: Annotated[list[UploadFile] | None, File()] = None,
) -> JobResult:
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
    code_files = code_files or []
    input_files = input_files or []
    await _save_files(paths.code, code_files)
    await _save_files(paths.input, input_files)

    result = await run_code(job_id, paths, job_spec)
    return result


@app.get("/jobs/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str):
    paths = _job_paths(job_id)
    path = paths.artifacts / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path)
