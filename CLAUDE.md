# Python Sandbox Executor

FastAPI-based job runner for executing Python code in isolated Docker containers.

## Tech Stack

- Python 3.12 + uv (package manager)
- FastAPI + Uvicorn
- Redis (queue, job metadata, logs, pub/sub)
- Docker (job sandboxing)

## Commands

```bash
# Development
uv sync               # Install dependencies
uv run main.py        # Start API server on :8000
uv run python worker.py  # Run worker separately (when INLINE_WORKER=0)

# Testing
uv run pytest         # Run tests (uses FAKE_REDIS=1, USE_DOCKER=0)

# Linting
uv run ruff check .   # Check code style

# Docker build
docker buildx build --platform linux/amd64,linux/arm64 -t job-runner:latest .
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.exec -t job-runner-exec:py3.12 .

# Docker Compose
API_IMAGE=ghcr.io/so2liu/python-sandbox-executor:latest \
EXEC_IMAGE=ghcr.io/so2liu/python-sandbox-executor-exec:py3.12 \
docker compose up
```

## Environment Variables

- `REDIS_URL` - Redis connection (default: `redis://localhost:6379/0`)
- `FAKE_REDIS` - Use fakeredis for testing (default: `0`)
- `JOB_DATA_DIR` - Job data directory (default: `data/jobs`)
- `INLINE_WORKER` - Run worker in API process (default: `1` for dev)
- `USE_DOCKER` - Enable Docker sandboxing (default: `1`)
- `JOB_RUN_IMAGE` - Executor image (default: `job-runner-exec:py3.12`)

## Project Structure

```
job_runner/
  api.py        # FastAPI endpoints
  models.py     # Pydantic schemas (JobSpec, JobRecord)
  runner.py     # Docker job execution
  job_store.py  # Redis job metadata storage
  log_store.py  # Redis log streaming (list + pub/sub)
  settings.py   # Environment config
worker.py       # Standalone worker process
```

## API Endpoints

- `POST /jobs` - Submit job (async, returns job_id)
- `POST /jobs/sync` - Submit job (sync, waits for completion)
- `GET /jobs/{id}` - Job status
- `GET /jobs/{id}/logs` - Full log (plain text)
- `GET /jobs/{id}/logs/stream` - SSE log stream
- `GET /jobs/{id}/artifacts/{filename}` - Download artifact

## Security Model

Jobs run in Docker with:
- Read-only root filesystem + tmpfs /tmp
- `--cap-drop=ALL`, `--security-opt no-new-privileges`
- CPU, memory, PID limits
- Network isolation (`none` or `outbound` only)
