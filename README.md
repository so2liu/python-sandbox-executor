# Job Runner (FastAPI + SSE)

Python 3.12 job runner that accepts user code/files, executes them in an isolated worker container, streams stdout/stderr via Server-Sent Events (SSE), and exposes a one-shot full-log endpoint. Uses `uv` for dependency management, Redis for queue/state/logs, and Pydantic for all schemas.

## Run

```bash
uv sync               # install deps into .venv
uv run main.py        # starts FastAPI on :8000
```

Environment:
- `JOB_DATA_DIR` (optional) – where job folders are created (`data/jobs` by default).
- `REDIS_URL` – Redis connection string (default `redis://localhost:6379/0`).
- `INLINE_WORKER` – run the worker inside the API process (default `1` for dev/tests). Set to `0` when running a separate worker.
- `USE_DOCKER` – run user code inside a sandboxed container (default `1`). Set to `0` for local/dev where Docker is unavailable.
- `JOB_RUN_IMAGE` – the sandbox image for jobs (default `job-runner-exec:py3.12`).

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
# Build executor image for jobs (contains pandas)
docker build -f Dockerfile.exec -t job-runner-exec:py3.12 .
```

Compose (Redis + API + worker + optional MinIO):
```bash
docker-compose up --build
```
API will listen on `localhost:8000`, Redis on `6379`. Data is persisted under `./data`.
The worker mounts the Docker socket to launch per-job containers using `JOB_RUN_IMAGE`.

### Offline docs & test page in image
- Static assets (README, docker-compose.yml, examples/client.html) are copied into the image and served at `/static`.
- Quick manual test page: open `/static/examples/client.html` when the API is running.

## CI / Publish (GitHub Actions)
- Workflow `.github/workflows/ci.yml`:
  - Runs `ruff check` and `pytest` (with fake Redis and inline worker).
  - Builds and pushes images to GHCR on `main` (`ghcr.io/<owner>/python-sandbox-executor:latest` and `...-exec:py3.12`).

To test a published image locally (replace `<owner>`):
```bash
docker pull ghcr.io/<owner>/python-sandbox-executor:latest
docker pull ghcr.io/<owner>/python-sandbox-executor-exec:py3.12
docker run -d --name jr-redis -p 6379:6379 redis:7-alpine
docker run -d --name jr-worker --net=host -e REDIS_URL=redis://localhost:6379/0 \
  -e INLINE_WORKER=0 -e USE_DOCKER=1 -e JOB_RUN_IMAGE=ghcr.io/<owner>/python-sandbox-executor-exec:py3.12 \
  -e JOB_DATA_DIR=/data/jobs -v /var/run/docker.sock:/var/run/docker.sock -v $(pwd)/data/jobs:/data/jobs \
  ghcr.io/<owner>/python-sandbox-executor:latest uv run python worker.py
docker run -d --name jr-api --net=host -e REDIS_URL=redis://localhost:6379/0 \
  -e INLINE_WORKER=0 -e USE_DOCKER=1 -e JOB_RUN_IMAGE=ghcr.io/<owner>/python-sandbox-executor-exec:py3.12 \
  -e JOB_DATA_DIR=/data/jobs -v $(pwd)/data/jobs:/data/jobs \
  ghcr.io/<owner>/python-sandbox-executor:latest
```

Then visit `http://localhost:8000/static/examples/client.html` to submit a job end-to-end.

## Tests

```bash
uv run pytest
```
