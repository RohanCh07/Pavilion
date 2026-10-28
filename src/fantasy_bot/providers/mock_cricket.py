"""Offline provider that plays a scripted 20-over cricket match, for demos and tests.

Overs are counted across both innings (1-20 India bat, 21-40 Australia bat). Every call to
``fixture_details`` advances the match by ``overs_per_poll``, so with the bot running you'll
see cricket alerts arrive on each poll until the result. Like the real scraper, it only
supplies raw scorecard stats; the scoring engine works out the points.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime

from fantasy_bot.domain import (
    CricketPosition,
    CricketStats,
    Fixture,
    FixtureDetails,
    PlayerInfo,
    PlayerLine,
    Series,
)

IND, AUS = 1, 2
FIXTURE_ID = 2001
SERIES_ID = 1
TOTAL_OVERS = 40
TEAM_NAMES = {IND: "India", AUS: "Australia"}
SHORT = {IND: "IND", AUS: "AUS"}

PLAYERS: tuple[PlayerInfo, ...] = (
    PlayerInfo(101, "Virat Kohli", IND, "India", CricketPosition.BATTER),
    PlayerInfo(102, "Rishabh Pant", IND, "India", CricketPosition.WICKET_KEEPER),
    PlayerInfo(103, "Hardik Pandya", IND, "India", CricketPosition.ALL_ROUNDER),
    PlayerInfo(104, "Jasprit Bumrah", IND, "India", CricketPosition.BOWLER),
    PlayerInfo(201, "Travis Head", AUS, "Australia", CricketPosition.BATTER),
    PlayerInfo(202, "Glenn Maxwell", AUS, "Australia", CricketPosition.ALL_ROUNDER),
    PlayerInfo(203, "Pat Cummins", AUS, "Australia", CricketPosition.BOWLER),
    PlayerInfo(204, "Adam Zampa", AUS, "Australia", CricketPosition.BOWLER),
)

# (over, player id, stat changes). Booleans are set, numbers are added.
SCRIPT: tuple[tuple[int, int, dict[str, int]], ...] = (
    # India bat
    (3, 101, {"batted": 1, "runs": 18, "balls_faced": 12, "fours": 3}),
    (3, 102, {"batted": 1, "runs": 10, "balls_faced": 6, "fours": 1, "sixes": 1}),
    (6, 102, {"out": 1}),  # c Maxwell b Cummins
    (6, 202, {"catches": 1}),
    (6, 203, {"balls_bowled": 12, "runs_conceded": 14, "wickets": 1}),
    (10, 101, {"runs": 22, "balls_faced": 14, "fours": 2, "sixes": 1}),
    (10, 103, {"batted": 1, "runs": 8, "balls_faced": 6}),
    (14, 101, {"runs": 12, "balls_faced": 8}),
    (14, 204, {"balls_bowled": 24, "runs_conceded": 28}),
    (18, 103, {"runs": 20, "balls_faced": 10, "sixes": 2, "out": 1}),  # b Cummins
    (18, 203, {"balls_bowled": 12, "runs_conceded": 16, "wickets": 1, "lbw_bowled": 1}),
    (20, 101, {"runs": 8, "balls_faced": 6}),
    (20, 202, {"balls_bowled": 24, "runs_conceded": 40}),
    # Australia bat
    (22, 201, {"batted": 1, "balls_faced": 2, "out": 1}),  # lbw b Bumrah, a duck
    (22, 104, {"balls_bowled": 6, "wickets": 1, "lbw_bowled": 1}),
    (28, 202, {"batted": 1, "runs": 35, "balls_faced": 20, "fours": 3, "sixes": 2}),
    (28, 104, {"balls_bowled": 12, "runs_conceded": 10, "maidens": 1}),
    (34, 202, {"out": 1}),  # c Pant b Pandya
    (34, 102, {"catches": 1}),
    (34, 103, {"balls_bowled": 18, "runs_conceded": 20, "wickets": 1}),
    (34, 203, {"batted": 1, "runs": 4, "balls_faced": 5, "out": 1}),  # run out Kohli
    (34, 101, {"run_outs_direct": 1}),
    (38, 204, {"batted": 1, "balls_faced": 1, "out": 1}),  # b Bumrah
    (38, 104, {"balls_bowled": 6, "runs_conceded": 5, "wickets": 1, "lbw_bowled": 1}),
)


class MockCricketProvider:
    def __init__(self, start: datetime | None = None, overs_per_poll: int = 4) -> None:
        self.start = start or datetime.now(UTC)
        self.over = 0
        self.overs_per_poll = overs_per_poll

    def _stats(self) -> dict[int, CricketStats]:
        stats = {p.id: CricketStats(in_xi=self.over > 0) for p in PLAYERS}
        for over, pid, changes in SCRIPT:
            if over > self.over:
                continue
            st = stats[pid]
            stats[pid] = replace(
                st,
                **{
                    k: True if isinstance(getattr(st, k), bool) else getattr(st, k) + n
                    for k, n in changes.items()
                },
            )
        return stats

    def _fixture(self, stats: dict[int, CricketStats]) -> Fixture:
        status = "NS" if self.over == 0 else "FT" if self.over >= TOTAL_OVERS else "LIVE"
        scores: dict[int, str] = {}
        for team, first_over in ((IND, 1), (AUS, 21)):
            if self.over < first_over:
                continue
            team_stats = [stats[p.id] for p in PLAYERS if p.team_id == team]
            runs = sum(s.runs for s in team_stats)
            wickets = sum(s.out for s in team_stats)
            overs = min(20, self.over - first_over + 1)
            scores[team] = f"{runs}/{wickets} ({overs}.0)"
        result = "India won" if status == "FT" else ""
        text = " · ".join(f"{SHORT[t]} {s}" for t, s in scores.items()) or "IND vs AUS"
        if result:
            text += f" · {result}"
        return Fixture(
            id=FIXTURE_ID,
            league_id=SERIES_ID,
            league_name="T20I (demo)",
            home_id=IND,
            home_name=TEAM_NAMES[IND],
            away_id=AUS,
            away_name=TEAM_NAMES[AUS],
            kickoff=self.start,
            status=status,
            score_text=text,
            format="t20",
            home_score=scores.get(IND, ""),
            away_score=scores.get(AUS, ""),
            result=result,
        )

    def _details(self) -> FixtureDetails:
        stats = self._stats()
        lines = tuple(PlayerLine(p, stats[p.id]) for p in PLAYERS)
        return FixtureDetails(self._fixture(stats), lines)

    async def search_players(self, query: str) -> list[PlayerInfo]:
        q = query.strip().lower()
        return [p for p in PLAYERS if q and q in p.name.lower()]

    async def fixtures_on(self, day: date) -> list[Fixture]:
        return [self._fixture(self._stats())] if day == self.start.date() else []

    async def fixture_details(self, fixture_ids: Sequence[int]) -> list[FixtureDetails]:
        if FIXTURE_ID not in fixture_ids:
            return []
        self.over = min(TOTAL_OVERS, self.over + self.overs_per_poll)
        return [self._details()]

    async def last_fixture_for_team(self, team_id: int) -> Fixture | None:
        return self._fixture(self._stats()) if team_id in (IND, AUS) else None

    async def list_series(self) -> list[Series]:
        status = {"NS": "upcoming", "LIVE": "live", "FT": "finished"}[
            self._fixture(self._stats()).status
        ]
        return [Series(SERIES_ID, "India vs Australia T20I (demo)", "IND vs AUS", status=status)]

    async def current_matches(self) -> list[Fixture]:
        return [self._fixture(self._stats())]

    async def series_matches(self, series_id: int) -> list[Fixture]:
        return [self._fixture(self._stats())] if series_id == SERIES_ID else []

    async def series_players(self, series_id: int) -> list[PlayerInfo]:
        return list(PLAYERS) if series_id == SERIES_ID else []

    async def aclose(self) -> None:
        return None
