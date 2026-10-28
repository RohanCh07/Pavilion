# Fantasy Points Bot

A Telegram bot for fantasy **football** and **cricket**. Pick the players in your squad, choose
a captain and vice-captain, and the bot messages you **live fantasy points** while they play:
goals, assists, saves, cards and clean sheets in football; runs, boundaries, milestones,
wickets, maidens, catches, stumpings and run outs in cricket; and a summary at the end.

```
📣 Live · Arsenal 1-0 Chelsea [1H 30']

⚽ Bukayo Saka (C) scored: +12 (×2)
```

```
📣 Live · NZ 180/5 (20.0) · IND 98/3 (12.0) [LIVE]

🏏 Tilak Varma (C) scored 22 runs: +44 (×2)
6️⃣ Tilak Varma (C) hit 1 six: +12 (×2)
🎉 Tilak Varma (C) earned the 25-run bonus: +8 (×2)
```

Data sources only ever supply **raw player stats**; the bot computes every point itself from
an editable TOML ruleset (Dream11-style by default). One bot instance runs one sport, picked by
`DATA_PROVIDER`:

| Provider | Sport | Source |
|---|---|---|
| `api_football` | football | [API-Football](https://www.api-football.com/) (free key, 100 requests/day) |
| `crex` | cricket | [CREX](https://crex.com) public scorecard pages, no key ([how it works](docs/ARCHITECTURE.md#crex-cricket-scraper)) |
| `mock` / `mock_cricket` | football / cricket | an offline scripted match, for trying it out |

There is also a phone-first **web app** (Pavilion) on a JSON API: users pick a series or
match, build any number of fantasy teams with a captain and vice-captain, edit them, and
follow each team's score and a leaderboard. Build it once (`cd web && npm install && npm run
build`), then `python -m fantasy_bot.api` serves both at <http://127.0.0.1:8000>. See
[docs/WEB.md](docs/WEB.md) and [docs/API.md](docs/API.md).

SofaScore was evaluated as a football source and rejected: it answers every non-browser
request with `403 Forbidden`, and getting past that would mean evading its bot protection.

## Quick start (Windows PowerShell)

```powershell
cd "D:\Projects\Fantasy Points Calculator"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env      # then edit .env
python -m fantasy_bot       # or: fantasy-bot
```

macOS/Linux: `source .venv/bin/activate` and `cp .env.example .env`.

### Configure `.env`

| Variable | Required | Default | Notes |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | | From [@BotFather](https://t.me/BotFather) |
| `DATA_PROVIDER` | | `api_football` | `api_football`, `crex`, or the demos `mock` / `mock_cricket` |
| `API_FOOTBALL_KEY` | with `api_football` | | Free plan: 100 requests/day |
| `LEAGUE_IDS` | | `39` | `api_football`: comma-separated. 39 Premier League, 140 La Liga, 135 Serie A, 78 Bundesliga, 2 Champions League |
| `SEASON` | | auto | `api_football`: season start year, e.g. `2026` |
| `CREX_SERIES` | | all | `crex`: series keys to follow, e.g. `2GR` from `crex.com/series/india-tour-of-new-zealand-2026-2GR` |
| `LIVE_POLL_SECONDS` | | `120` | Poll interval during tracked matches (min 30) |
| `SCHEDULE_REFRESH_SECONDS` | | `10800` | How often the day's fixture list is reloaded |
| `SCORING_RULESET` | | by sport | `dream11_football` or `dream11_cricket`, or a path to your own `.toml` |
| `SQUAD_SIZE` | | `11` | |
| `DATABASE_URL` | | `sqlite+aiosqlite:///data/fantasy.db` | Postgres: `postgresql+asyncpg://…` (`pip install -e ".[postgres]"`) |
| `LOG_LEVEL` | | `INFO` | |

### Try the demo

Set `DATA_PROVIDER=mock`, start the bot, then in Telegram:

1. `/add saka`, `/add raya`, `/add palmer` and tap each result.
2. `/team` and tap 👑 next to Saka.
3. Wait: every poll advances the demo match 15 minutes, so alerts arrive one by one until full time.

For cricket, set `DATA_PROVIDER=mock_cricket` and add `kohli`, `bumrah` and `maxwell`. Each
poll advances the scripted T20 by four overs.

### Real cricket with CREX

Set `DATA_PROVIDER=crex` (no key needed). On startup the bot reads each listed match's squad
page in the background, one at a time, which takes about a minute; a search made before that
finishes waits for it, and later searches are instant. Set
`CREX_SERIES` to the series you play to keep it fast and focused. CREX's terms allow personal,
non-commercial use, so keep the bot to that.

## Deploy

One Docker image runs the web app/API and the bot; `docker compose up -d --build` starts both
with Postgres. Platforms like Render or Railway can build straight from the repo. See
[docs/DEPLOY.md](docs/DEPLOY.md).

## Commands

| Command | What it does |
|---|---|
| `/add <name>` | Search and add a player to your squad |
| `/team` | Squad with latest-match points; buttons to set C / VC or remove |
| `/calc <name>` | Points breakdown from a player's latest (or live) match. Typing a name alone does the same |
| `/fixtures` | Today's matches in the followed leagues or series |
| `/rules` | The active scoring rules |
| `/alerts on\|off` | Turn live alerts on or off |
| `/help` | Command list |

## Development

```powershell
pytest              # 124 tests: scoring, mapping, CREX parsing, storage, the web API, simulated matches
ruff check src tests
ruff format src tests
```

## Project layout

```
src/fantasy_bot/
├── __main__.py           entry point (python -m fantasy_bot)
├── config.py             typed settings from env / .env
├── domain.py             provider-agnostic models: Fixture, PlayerStats, CricketStats, ...
├── messages.py           all user-facing text (Telegram HTML)
├── scoring/
│   ├── engine.py         pure points calculation (football) and sport dispatch
│   ├── cricket.py        cricket rules and points calculation
│   ├── rules.py          ruleset loader
│   └── rulesets/*.toml   scoring rules as data
├── providers/
│   ├── base.py           DataProvider protocol
│   ├── api_football.py   HTTP client (quota-aware, cached, retries)
│   ├── api_football_mapper.py  raw JSON -> domain
│   ├── crex.py           CREX scraper (polite, cached)
│   ├── crex_parser.py    CREX page JSON -> domain
│   ├── mock.py           scripted offline football match
│   └── mock_cricket.py   scripted offline T20
├── storage/              SQLAlchemy async models + repository
├── live/
│   ├── events.py         snapshot diff -> point changes
│   └── tracker.py        schedule-driven polling and alert fan-out
├── fantasy/service.py    fantasy teams: validation, editing, scores, leaderboards
├── api/                  web API for a front end (FastAPI): app, schemas, entry point
├── bot/                  Telegram handlers, keyboards, notifier, app wiring
└── utils/cache.py        small TTL cache
tests/                    pytest suite (fixtures/crex: trimmed real CREX page data)
web/                      phone-first web app (React API on Preact, Vite, Tailwind)
docs/                     architecture, scoring format, roadmap
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SCORING.md](docs/SCORING.md),
[docs/API.md](docs/API.md), [docs/WEB.md](docs/WEB.md), [docs/DEPLOY.md](docs/DEPLOY.md),
[docs/ROADMAP.md](docs/ROADMAP.md).
