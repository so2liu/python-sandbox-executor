FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential docker.io && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN UV_NO_CACHE=1 uv sync --frozen --no-dev

COPY . .
ENV JOB_DATA_DIR=/data/jobs
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "job_runner.api:app", "--host", "0.0.0.0", "--port", "8000"]
