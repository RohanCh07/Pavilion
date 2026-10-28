# Web API

A JSON API for a front end: browse series and matches, build fantasy teams for a whole
series or a single match, pick captain and vice-captain, edit or delete teams, and see each
team's fantasy score and a leaderboard.

It runs alongside (or instead of) the Telegram bot and shares the same scoring engine and
rules. Data providers only supply raw player stats; every point is computed from the ruleset.

## Run it

```powershell
pip install -e ".[api]"          # or ".[dev]", which includes it
$env:DATA_PROVIDER = "crex"       # or put it in .env; "mock_cricket" for an offline demo
python -m fantasy_bot.api         # or: fantasy-api
```

Then open <http://127.0.0.1:8000/docs> for interactive docs where you can try every call.
No Telegram token is needed for the API. If the web app has been built (`web/dist`, see
[WEB.md](WEB.md)), it's served at <http://127.0.0.1:8000> too.

| Variable | Default | Notes |
|---|---|---|
| `DATA_PROVIDER` | | `crex` or `mock_cricket` (series support is cricket-only for now) |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Use `0.0.0.0` to reach it from other devices |
| `API_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Front-end origins allowed to call the API |
| `TEAM_MIN_PLAYERS` / `TEAM_MAX_PLAYERS` | `1` / `11` | Team size limits |
| `WEB_DIST` | `web/dist` | Built web app to serve at `/` |
| `DATABASE_URL`, `SCORING_RULESET`, `CREX_SERIES` | | As for the bot (see README) |

## Users

Calls that create, change or list *your* teams need an `X-User-Id` header: any stable string
the front end picks for the user (for example a Telegram user id). It's a placeholder for real
login, so don't expose the API publicly until authentication sits in front of it. Reading a
team, its score and leaderboards needs no header.

## Concepts

- **Series**: a tour, tournament or league (e.g. "India tour of New Zealand 2026").
- **Match**: one game in a series. `status` is `NS` (not started), `LIVE` or `FT` (finished).
- **Team**: a user's picks for a whole series (`match_id` null) or for one match.
  - A user can have any number of teams.
  - Between `TEAM_MIN_PLAYERS` and `TEAM_MAX_PLAYERS` players, each picked once.
  - At most one captain (2x points) and one vice-captain (1.5x).
  - Series teams pick from every squad in the series; match teams only from that match's two sides.
  - A match team locks when its match starts. A series team can be edited any time, and its
    score is always computed with its current players.
- **Score**: a team's points in every started match of its series (or its one match), per
  player and per match. Live matches count their points so far.

All ids are integers.

## Pools

A pool groups any number of teams for one series or one match and ranks them on its own
leaderboard. Its creator adds, edits and deletes its teams (for example one per friend).

- **normal**: no team rules. Any number of players (1-30), captain and vice-captain optional,
  and the same player can be in many teams. A normal pool must be created with at least one team.
- **dream**: Dream11-style rules for every team: exactly 11 players, one captain and one
  vice-captain, 1-4 WK, 3-6 BAT, 1-4 AR, 3-6 BOWL, and at most 7 from one side in a match
  pool. A dream pool can be created empty.

A match pool locks when its match starts. Pool teams don't appear in `GET /api/teams` or in
series leaderboards; they belong to their pool.

```http
POST /api/pools
X-User-Id: rohan

{
  "name": "Office League",
  "type": "normal",
  "series_id": 3195,
  "match_id": 49947,
  "teams": [
    {"name": "Rohan", "players": [{"player_id": 1502, "role": "captain"}, {"player_id": 423}]},
    {"name": "Amit", "players": [{"player_id": 1502}, {"player_id": 817, "role": "captain"}]}
  ]
}
```

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness and the sport being served |
| GET | `/api/rules` | Ruleset name, C/VC multipliers, team size limits |
| GET | `/api/series` | Current series |
| GET | `/api/series/{series_id}/matches` | Matches in a series, oldest first |
| GET | `/api/series/{series_id}/players?match_id=&q=` | Players you can pick (optionally one match's sides, or a name search) |
| GET | `/api/series/{series_id}/matches/{match_id}/scorecard` | Raw stats and points for every player in a match |
| GET | `/api/series/{series_id}/leaderboard?match_id=` | Series teams ranked by points (or one match's teams) |
| GET | `/api/teams?series_id=&match_id=` | Your teams (needs `X-User-Id`) |
| POST | `/api/teams` | Create a team (needs `X-User-Id`) |
| GET | `/api/teams/{team_id}` | One team |
| PATCH | `/api/teams/{team_id}` | Rename and/or replace the line-up (owner only) |
| PUT | `/api/teams/{team_id}/role` | Set a player's role; captain or vice-captain moves off whoever had it (owner only) |
| DELETE | `/api/teams/{team_id}` | Delete a team (owner only) |
| GET | `/api/teams/{team_id}/score` | Points per match, per player and in total |
| GET | `/api/pools` | Your pools, with team counts (needs `X-User-Id`) |
| POST | `/api/pools` | Create a pool with its first teams (needs `X-User-Id`) |
| GET | `/api/pools/{pool_id}` | A pool and its leaderboard (teams ranked by points) |
| PATCH | `/api/pools/{pool_id}` | Rename a pool (creator only) |
| DELETE | `/api/pools/{pool_id}` | Delete a pool and its teams (creator only) |
| POST | `/api/pools/{pool_id}/teams` | Add a team to a pool (creator only); edit or delete it with the team endpoints |

Errors come back as `{"detail": "..."}` with: `401` no `X-User-Id`, `403` not your team,
`404` not found, `409` match already started (team locked), `422` invalid team,
`503` the data source isn't answering.

## Examples

Create a series team with a captain and vice-captain:

```http
POST /api/teams
X-User-Id: rohan
Content-Type: application/json

{
  "name": "Rohan XI",
  "series_id": 3195,
  "players": [
    {"player_id": 1502, "role": "captain"},
    {"player_id": 423, "role": "vice_captain"},
    {"player_id": 817},
    {"player_id": 254}
  ]
}
```

Add `"match_id": 49946` to make it a team for just that match instead.

Make another player captain:

```http
PUT /api/teams/1/role
X-User-Id: rohan

{"player_id": 817, "role": "captain"}
```

Team score (trimmed):

```json
{
  "team": {"id": 1, "name": "Rohan XI", "series_name": "India tour of New Zealand 2026", "...": "..."},
  "points": 1073.0,
  "players": [
    {"player_id": 1502, "name": "Tilak Varma", "role": "captain", "points": 258.0},
    {"player_id": 423, "name": "Mitchell Santner", "role": "vice_captain", "points": 342.0}
  ],
  "matches": [
    {
      "match": {"id": 49945, "status": "FT", "score": "NZ 180/5 (20.0) · IND 181/6 (19.5) · India won by 4 wickets", "...": "..."},
      "points": 622.0,
      "players": [
        {
          "player_id": 1502, "name": "Tilak Varma", "role": "captain", "played": true,
          "base": 115.0, "multiplier": 2.0, "points": 230.0,
          "lines": [{"key": "runs", "label": "Runs", "count": 51, "points": 51.0}, "..."]
        }
      ]
    }
  ]
}
```

## How scoring data flows

`GET .../score` loads every started match of the team's series. A finished match's raw stats
are stored in the `match_scorecards` table the first time they're fetched, so later scores
and leaderboards never scrape that match again. Live matches are fetched from the provider,
which caches each scorecard for 20 seconds. The first score for a series can take a few
seconds per match, because CREX pages are fetched one at a time.

Code: `fantasy/service.py` (rules for teams and scoring), `api/app.py` (routes),
`api/schemas.py` (JSON shapes), `storage/teams.py` (tables).
