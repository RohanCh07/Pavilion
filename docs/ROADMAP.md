# Roadmap

Carried over from the earlier design in `D:\Projects\BOT\docs\ROADMAP.md`.

## Phase 1: Reliable core ✅

- [x] Provider abstraction (`FootballProvider`) with API-Football and an offline mock
- [x] Mapper normalising raw API data into domain models
- [x] Data-driven scoring engine (TOML rulesets)
- [x] Async storage (SQLite by default, Postgres-ready)
- [x] Background polling driven by the fixture schedule
- [x] Test suite for scoring, mapping, storage and a full simulated match

## Cricket ✅

- [x] `CricketStats`, cricket positions and a Dream11 T20 ruleset
- [x] CREX scraper for schedule, live scorecards and squads (raw stats only)
- [x] Offline scripted T20 (`mock_cricket`)
- [x] ODI and Test rulesets; each match is scored with its format's rules
- [ ] Dot-ball points, if a source that publishes them is added

## Phase 2: Personal fantasy experience (mostly done)

- [x] Squad building (`/add`, `/team`), captain and vice-captain
- [x] Live event detection and personalised alerts
- [x] Full-time summaries
- [ ] Lineup alerts before kickoff (API-Football `/fixtures/lineups`)
- [ ] `/match` live centre for one fixture

## Phase 3: Social

- [ ] Group chats and contests (`/createcontest`)
- [ ] Live leaderboards and rank-change alerts
- [ ] Post-match MVP

## Phase 4: Insights

- [ ] Player profiles and fantasy history
- [ ] Player comparison
- [ ] Fixture difficulty and pick suggestions

## Phase 5: Web app

- [x] HTTP API over the same core packages: series, matches, teams, scores, leaderboards
- [ ] Real authentication (e.g. Telegram Login) instead of the `X-User-Id` header
- [x] Phone-first web app (`web/`, from the Stitch Pavilion design)
- [ ] Football series support (API-Football leagues) in the API
- [ ] Contest rules such as credits and max players per side
