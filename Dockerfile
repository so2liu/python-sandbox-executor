FROM python:3.12-slim

WORKDIR /app

# Install CJK fonts for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

# Force matplotlib to rebuild its font cache with all available fonts
RUN uv run python -c "import matplotlib.font_manager as fm; fm._load_fontmanager(try_read_cache=False)"

COPY . .

EXPOSE 8765

CMD ["uv", "run", "main.py"]
