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

# Clear matplotlib font cache so it's rebuilt on first run with new fonts
RUN rm -rf /root/.cache/matplotlib

COPY . .

EXPOSE 8765

CMD ["uv", "run", "main.py"]
