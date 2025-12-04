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

# Rebuild matplotlib font cache after installing fonts and matplotlib
RUN uv run python -c "import matplotlib.font_manager; matplotlib.font_manager._rebuild()"

COPY . .

EXPOSE 8765

CMD ["uv", "run", "main.py"]
