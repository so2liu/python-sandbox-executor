FROM python:3.12-slim

WORKDIR /app

# Install CJK fonts for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

COPY . .

EXPOSE 8765

CMD ["uv", "run", "main.py"]
