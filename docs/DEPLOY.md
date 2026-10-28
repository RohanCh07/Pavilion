# Deploying

The project ships as one Docker image that runs two processes:

| Process | Command | What it does |
|---|---|---|
| Web app + API | `fantasy-api` (the image's default) | Serves the Pavilion web app at `/`, the JSON API at `/api`, and `/health` |
| Telegram bot | `fantasy-bot` | Live alerts and commands in Telegram |

Both use the same database. Run the bot only if you've set `TELEGRAM_BOT_TOKEN`, and run
exactly one bot instance (Telegram allows one poller per token).

## Configuration

Everything is set with environment variables (see `.env.example`). The ones that matter in
production:

| Variable | Value |
|---|---|
| `DATA_PROVIDER` | `crex` |
| `DATABASE_URL` | Postgres: `postgresql+asyncpg://user:pass@host:5432/db`. Default: SQLite at `/data/fantasy.db` (needs a persistent volume on `/data`) |
| `TELEGRAM_BOT_TOKEN` | From @BotFather. Only the bot needs it |
| `PORT` / `API_PORT` | Most hosts set `PORT` for you; the API listens on it, on `0.0.0.0` |
| `API_CORS_ORIGINS` | Only if the web app is served from a different domain than the API |
| `CREX_SERIES` | Optional: limit to some series |
| `LOG_LEVEL` | `INFO` |

Tables are created on first start, and newer columns are added to older databases
automatically.

## Option A: one server with Docker Compose

On any VPS with Docker:

```bash
git clone <your repo> fantasy && cd fantasy
cp .env.example .env        # set DATA_PROVIDER=crex and TELEGRAM_BOT_TOKEN
docker compose up -d --build
```

This starts the web app on port 8000, the bot, and a Postgres database whose data lives in
the `pgdata` volume. Put a reverse proxy (Caddy, Nginx) in front for HTTPS. To update:
`git pull && docker compose up -d --build`.

Not using the bot? `docker compose up -d api db`.

## Option B: Render (blueprint)

`render.yaml` sets everything up: the web app (free plan), the Telegram bot (a paid
background worker; delete its block to skip it) and a Postgres database.

1. In Render: **New > Blueprint**, pick the repo, and apply.
2. When asked, fill in `TELEGRAM_BOT_TOKEN` (and `CREX_SERIES` if you want to limit series).
3. Open the web service's URL. Every push to `main` redeploys.

Free web services sleep after a while without visits, so the first visit after that takes
up to a minute. Render's free Postgres has a time limit, so move it to a paid plan to keep
your data long term. Check Render's current pricing page for the details.

## Option B2: other platforms that build from your repo (Railway, Fly.io, ...)

1. Connect the repository and choose **Docker** as the build method (the `Dockerfile` is at
   the root).
2. Web service: no start command needed (the image runs `fantasy-api`). Health check path:
   `/health`.
3. Database: add the platform's Postgres and set `DATABASE_URL` to its connection string
   (a plain `postgres://` URL is fine; the app switches it to the async driver). Or attach a persistent disk at `/data`
   to keep the default SQLite.
4. Set `DATA_PROVIDER=crex` (and any other variables above).
5. Bot (optional): add a **background worker** from the same repo with start command
   `fantasy-bot`, the same `DATABASE_URL`, and `TELEGRAM_BOT_TOKEN`.

## Option C: without Docker

```bash
pip install ".[api,postgres]"
cd web && npm ci && npm run build && cd ..
fantasy-api      # and, separately, fantasy-bot
```

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request: lint and tests (Python 3.12),
the web build, and a Docker image build.

## Before sharing the app publicly

- **Login:** users are identified by the name they type (`X-User-Id`), so anyone can act as
  anyone. Fine for friends; add real login (planned: Telegram Login) before going public.
- **CREX:** its terms allow personal, non-commercial use. The scraper is polite (one request
  at a time, cached), but a busy public site would multiply requests.
- **Backups:** back up the Postgres database (or the `/data` volume for SQLite).
