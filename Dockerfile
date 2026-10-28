# One image for both processes:
#   web API + web app:  docker run ... (default command, fantasy-api)
#   Telegram bot:       docker run ... fantasy-bot
# See docs/DEPLOY.md.

# --- 1. Build the web app ------------------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- 2. Python runtime -------------------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[api,postgres]"

COPY --from=web /web/dist ./web/dist

# SQLite lives on a volume at /data unless DATABASE_URL points at Postgres.
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown app /data
ENV WEB_DIST=/app/web/dist \
    DATABASE_URL=sqlite+aiosqlite:////data/fantasy.db \
    API_HOST=0.0.0.0 \
    API_PORT=8000
VOLUME ["/data"]
USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", os.environ.get(\"API_PORT\", \"8000\"))}/health', timeout=4)" || exit 1

CMD ["fantasy-api"]
