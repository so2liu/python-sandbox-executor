# Job Runner (FastAPI + SSE)

Python 3.12 job runner that accepts user code/files, executes them in a background worker, streams stdout/stderr via Server-Sent Events (SSE), and exposes a one-shot full-log endpoint. Uses `uv` for dependency management, Redis for queue/state/logs, and Pydantic for all schemas.

## Run

```bash
uv sync               # install deps into .venv
uv run main.py        # starts FastAPI on :8000
```

Environment:
- `JOB_DATA_DIR` (optional) – where job folders are created (`data/jobs` by default).
- `REDIS_URL` – Redis connection string (default `redis://localhost:6379/0`).
- `INLINE_WORKER` – run the worker inside the API process (default `1` for dev/tests). Set to `0` when running a separate worker.

## API (SSE only, no WebSocket)
- `POST /jobs` (multipart): field `spec` contains JSON spec (entry, args, timeout, etc.); `code_files` and `input_files` are optional uploads.
- `GET /jobs/{id}`: job status + metadata.
- `GET /jobs/{id}/logs`: full log snapshot (plain text).
- `GET /jobs/{id}/logs/stream`: SSE stream of stdout/stderr (`data:` lines, ends with `event: end`).
- `GET /jobs/{id}/artifacts/{filename}`: download produced file.

`JobSpec` JSON example:
```json
{
  "entry": "main.py",
  "args": ["--foo", "bar"],
  "timeout_sec": 60,
  "runtime": "python3.12",
  "net_policy": "none",
  "env": {"EXAMPLE": "1"}
}
```

Example create request:
```bash
curl -X POST http://localhost:8000/jobs \
  -F spec='{"entry":"main.py","timeout_sec":20}' \
  -F code_files=@examples/main.py
```

Tail logs (SSE):
```bash
curl -N http://localhost:8000/jobs/<jobId>/logs/stream
```

## Worker (separate process)

If you disable `INLINE_WORKER`, run the worker separately:
```bash
uv run python worker.py
```

## Docker / Compose

Build:
```bash
docker build -t job-runner:latest .
```

Compose (Redis + API + worker + optional MinIO):
```bash
docker-compose up --build
```
API will listen on `localhost:8000`, Redis on `6379`. Data is persisted under `./data`.

## Tests

```bash
uv run pytest
```
