FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM python:3.15-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable --python /usr/local/bin/python

FROM python:3.15-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS runtime
LABEL org.opencontainers.image.source="https://github.com/Abdel-Abdelaal/shortlink"
RUN groupadd --gid 10001 shortlink \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin shortlink \
    && mkdir /data \
    && chown 10001:10001 /data
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHORTLINK_DATABASE_PATH=/data/shortlink.db \
    SHORTLINK_BASE_URL=http://127.0.0.1:8000
WORKDIR /app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close()"]
CMD ["uvicorn", "shortlink.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
