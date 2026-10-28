"""Fantasy teams for a series or a match: validation, editing and scoring.

The web API (and any future front end) talks to this service, never to providers or storage
directly. Points always come from the scoring engine and the ruleset; providers only supply
raw stats, which are fetched per match and cached in the database once a match is finished.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from fantasy_bot.domain import (
    POOL_KINDS,
    CricketPosition,
    FantasyTeam,
    Fixture,
    FixtureDetails,
    PlayerInfo,
    Pool,
    Role,
    Series,
    TeamPick,
)
from fantasy_bot.providers import ProviderError, SeriesProvider
from fantasy_bot.scoring import PointsResult, Rules, calculate_points
from fantasy_bot.storage import TeamRepository

log = logging.getLogger(__name__)


class TeamError(ValueError):
    """A request the service refuses. ``kind`` maps to an HTTP status in the API."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind  # "not_found", "invalid", "forbidden", "locked"


@dataclass(frozen=True, slots=True)
class TeamLimits:
    min_players: int = 1
    max_players: int = 11
    name_length: int = 40


@dataclass(frozen=True, slots=True)
class DreamTeamRules:
    """Team rules for "dream" pools, as on Dream11. "normal" pools have none."""

    players: int = 11
    max_from_one_side: int = 7  # match pools only
    roles: tuple[tuple[CricketPosition, int, int], ...] = (
        (CricketPosition.WICKET_KEEPER, 1, 4),
        (CricketPosition.BATTER, 3, 6),
        (CricketPosition.ALL_ROUNDER, 1, 4),
        (CricketPosition.BOWLER, 3, 6),
    )


DREAM = DreamTeamRules()
NORMAL_POOL_MAX_PLAYERS = 30  # "no rules", but a sane upper bound


@dataclass(frozen=True, slots=True)
class PlayerScore:
    pick: TeamPick
    played: bool
    result: PointsResult  # with the pick's captain / vice-captain multiplier applied


@dataclass(frozen=True, slots=True)
class MatchScore:
    fixture: Fixture
    players: tuple[PlayerScore, ...]
    total: float


@dataclass(frozen=True, slots=True)
class TeamScore:
    team: FantasyTeam
    matches: tuple[MatchScore, ...]
    total: float
    player_totals: dict[int, float] = field(default_factory=dict)  # player id -> series total


class FantasyService:
    def __init__(
        self,
        provider: SeriesProvider,
        teams: TeamRepository,
        rules: Rules,
        limits: TeamLimits | None = None,
    ) -> None:
        self._provider = provider
        self._teams = teams
        self._rules = rules
        self.limits = limits or TeamLimits()

    @property
    def rules(self) -> Rules:
        return self._rules

    async def aclose(self) -> None:
        await self._provider.aclose()

    # Browsing ----------------------------------------------------------------------------

    async def list_series(self) -> list[Series]:
        return await self._provider.list_series()

    async def series(self, series_id: int) -> Series:
        found = next((s for s in await self.list_series() if s.id == series_id), None)
        if found:
            return found
        matches = await self._provider.series_matches(series_id)
        if not matches:
            raise TeamError("not_found", f"Series {series_id} not found.")
        return Series(series_id, matches[0].league_name or str(series_id))

    async def current_matches(self) -> list[Fixture]:
        """Live, recent and upcoming matches across all series, soonest first."""
        return sorted(await self._provider.current_matches(), key=lambda f: f.kickoff)

    async def series_matches(self, series_id: int) -> list[Fixture]:
        return await self._provider.series_matches(series_id)

    async def match(self, series_id: int, match_id: int) -> Fixture:
        found = next((f for f in await self.series_matches(series_id) if f.id == match_id), None)
        if found is None:
            raise TeamError("not_found", f"Match {match_id} is not in series {series_id}.")
        return found

    async def players(
        self, series_id: int, match_id: int | None = None, query: str = ""
    ) -> list[PlayerInfo]:
        """Players a team for this series (or match) may pick, optionally filtered by name."""
        players = await self._provider.series_players(series_id)
        if match_id is not None:
            teams = (await self.match(series_id, match_id)).team_ids
            players = [p for p in players if p.team_id in teams]
        q = query.strip().lower()
        if q:
            players = [p for p in players if q in p.name.lower()]
        return sorted(players, key=lambda p: (p.team_name, p.name))

    async def match_details(self, fixture: Fixture, series_id: int) -> FixtureDetails | None:
        """Raw stats for a match; None before it starts. Finished matches come from the DB."""
        cached = (await self._teams.get_scorecards([fixture.id])).get(fixture.id)
        if cached:
            return cached
        if fixture.status == "NS":
            return None
        try:
            found = await self._provider.fixture_details([fixture.id])
        except ProviderError:
            log.exception("Stats for match %s unavailable", fixture.id)
            return None
        details = found[0] if found else None
        if details and details.fixture.is_finished:
            await self._teams.save_scorecard(series_id, details)
        return details

    # Teams -------------------------------------------------------------------------------

    async def _validate(
        self,
        series_id: int,
        match_id: int | None,
        name: str,
        picks: Sequence[tuple[int, Role]],
        kind: str | None = None,
    ) -> tuple[str, list[TeamPick]]:
        """Check a team. ``kind`` is the pool type ("normal", "dream") or None outside pools."""
        name = name.strip()
        if not name or len(name) > self.limits.name_length:
            raise TeamError("invalid", f"Team name must be 1-{self.limits.name_length} characters.")
        ids = [pid for pid, _ in picks]
        if len(set(ids)) != len(ids):
            raise TeamError("invalid", "A player can only be picked once in a team.")
        low, high = {
            None: (self.limits.min_players, self.limits.max_players),
            "normal": (1, NORMAL_POOL_MAX_PLAYERS),
            "dream": (DREAM.players, DREAM.players),
        }[kind]
        if not low <= len(ids) <= high:
            raise TeamError(
                "invalid", f"Pick {low} players." if low == high else f"Pick {low}-{high} players."
            )
        roles = [role for _, role in picks]
        for role in (Role.CAPTAIN, Role.VICE_CAPTAIN):
            label = role.value.replace("_", "-")
            if roles.count(role) > 1:
                raise TeamError("invalid", f"Only one {label} allowed.")
            if kind == "dream" and roles.count(role) == 0:
                raise TeamError("invalid", f"A Dream Team needs a {label}.")

        squad = {p.id: p for p in await self.players(series_id, match_id)}
        unknown = [pid for pid in ids if pid not in squad]
        if unknown:
            where = f"match {match_id}" if match_id is not None else f"series {series_id}"
            raise TeamError("invalid", f"Players {unknown} are not in the squads for {where}.")
        team = [TeamPick(squad[pid], role) for pid, role in picks]
        if kind == "dream":
            self._check_dream(team, match_id is not None)
        return name, team

    @staticmethod
    def _check_dream(team: Sequence[TeamPick], one_match: bool) -> None:
        for position, low, high in DREAM.roles:
            n = sum(p.player.position == position for p in team)
            if not low <= n <= high:
                label = position.value.replace("_", "-")
                raise TeamError("invalid", f"A Dream Team needs {low}-{high} {label}s (has {n}).")
        if one_match:
            sides: dict[str, int] = {}
            for p in team:
                sides[p.player.team_name] = sides.get(p.player.team_name, 0) + 1
            for side, n in sides.items():
                if n > DREAM.max_from_one_side:
                    raise TeamError(
                        "invalid",
                        f"A Dream Team can have at most {DREAM.max_from_one_side} players from "
                        f"one side ({n} from {side}).",
                    )

    async def _pool_kind(self, team: FantasyTeam) -> str | None:
        if team.pool_id is None:
            return None
        pool = await self._teams.get_pool(team.pool_id)
        return pool.kind if pool else None

    async def _check_editable(self, team: FantasyTeam, owner: str) -> None:
        if team.owner != owner:
            raise TeamError("forbidden", "Only the team's owner can change it.")
        if team.match_id is not None:
            fixture = await self.match(team.series_id, team.match_id)
            if fixture.status != "NS":
                raise TeamError("locked", "The match has started, so this team is locked.")

    async def create_team(
        self,
        owner: str,
        name: str,
        series_id: int,
        picks: Sequence[tuple[int, Role]],
        match_id: int | None = None,
    ) -> FantasyTeam:
        series = await self.series(series_id)
        if match_id is not None:
            fixture = await self.match(series_id, match_id)
            if fixture.status != "NS":
                raise TeamError("locked", "That match has already started.")
        name, team_picks = await self._validate(series_id, match_id, name, picks)
        return await self._teams.create(owner, name, series_id, series.name, match_id, team_picks)

    async def get_team(self, team_id: int) -> FantasyTeam:
        team = await self._teams.get(team_id)
        if team is None:
            raise TeamError("not_found", f"Team {team_id} not found.")
        return team

    async def list_teams(
        self, owner: str | None = None, series_id: int | None = None, match_id: int | None = None
    ) -> list[FantasyTeam]:
        """Teams outside pools (pool teams are listed with their pool)."""
        return await self._teams.find(owner=owner, series_id=series_id, match_id=match_id)

    # Pools -------------------------------------------------------------------------------

    async def create_pool(
        self,
        owner: str,
        name: str,
        kind: str,
        series_id: int,
        teams: Sequence[tuple[str, Sequence[tuple[int, Role]]]],
        match_id: int | None = None,
    ) -> Pool:
        """Create a pool with its first teams. A "normal" pool needs at least one team."""
        name = name.strip()
        if not name or len(name) > self.limits.name_length:
            raise TeamError("invalid", f"Pool name must be 1-{self.limits.name_length} characters.")
        if kind not in POOL_KINDS:
            raise TeamError("invalid", f"Pool type must be one of: {', '.join(POOL_KINDS)}.")
        if kind == "normal" and not teams:
            raise TeamError("invalid", "A normal pool needs at least one team.")
        series = await self.series(series_id)
        if match_id is not None:
            fixture = await self.match(series_id, match_id)
            if fixture.status != "NS":
                raise TeamError("locked", "That match has already started.")
        checked = [await self._validate(series_id, match_id, n, p, kind) for n, p in teams]
        pool = await self._teams.create_pool(owner, name, kind, series_id, series.name, match_id)
        for team_name, picks in checked:
            await self._teams.create(
                owner, team_name, series_id, series.name, match_id, picks, pool_id=pool.id
            )
        return pool

    async def get_pool(self, pool_id: int) -> Pool:
        pool = await self._teams.get_pool(pool_id)
        if pool is None:
            raise TeamError("not_found", f"Pool {pool_id} not found.")
        return pool

    async def list_pools(self, owner: str) -> list[tuple[Pool, int]]:
        """The user's pools, newest first, each with its number of teams."""
        pools = await self._teams.find_pools(owner)
        counts = await self._teams.pool_team_counts([p.id for p in pools])
        return [(p, counts.get(p.id, 0)) for p in pools]

    async def pool_teams(self, pool_id: int) -> list[FantasyTeam]:
        return await self._teams.find(pool_id=pool_id)

    async def add_pool_team(
        self, pool_id: int, owner: str, name: str, picks: Sequence[tuple[int, Role]]
    ) -> FantasyTeam:
        pool = await self.get_pool(pool_id)
        if pool.owner != owner:
            raise TeamError("forbidden", "Only the pool's creator can add teams.")
        if pool.match_id is not None:
            fixture = await self.match(pool.series_id, pool.match_id)
            if fixture.status != "NS":
                raise TeamError("locked", "The match has started, so this pool is locked.")
        team_name, team_picks = await self._validate(
            pool.series_id, pool.match_id, name, picks, pool.kind
        )
        return await self._teams.create(
            owner, team_name, pool.series_id, pool.series_name, pool.match_id, team_picks,
            pool_id=pool.id,
        )  # fmt: skip

    async def rename_pool(self, pool_id: int, owner: str, name: str) -> Pool:
        pool = await self.get_pool(pool_id)
        if pool.owner != owner:
            raise TeamError("forbidden", "Only the pool's creator can rename it.")
        name = name.strip()
        if not name or len(name) > self.limits.name_length:
            raise TeamError("invalid", f"Pool name must be 1-{self.limits.name_length} characters.")
        renamed = await self._teams.rename_pool(pool_id, name)
        assert renamed is not None
        return renamed

    async def delete_pool(self, pool_id: int, owner: str) -> None:
        pool = await self.get_pool(pool_id)
        if pool.owner != owner:
            raise TeamError("forbidden", "Only the pool's creator can delete it.")
        await self._teams.delete_pool(pool_id)

    async def pool_leaderboard(self, pool_id: int) -> tuple[Pool, list[TeamScore]]:
        """The pool and its teams' scores, best first."""
        pool = await self.get_pool(pool_id)
        cache: dict[int, FixtureDetails | None] = {}
        scores = [await self._team_score(t, cache) for t in await self.pool_teams(pool_id)]
        return pool, sorted(scores, key=lambda s: -s.total)

    async def update_team(
        self,
        team_id: int,
        owner: str,
        *,
        name: str | None = None,
        picks: Sequence[tuple[int, Role]] | None = None,
    ) -> FantasyTeam:
        team = await self.get_team(team_id)
        await self._check_editable(team, owner)
        current = [(p.player.id, p.role) for p in team.picks]
        new_name, new_picks = await self._validate(
            team.series_id,
            team.match_id,
            team.name if name is None else name,
            current if picks is None else picks,
            await self._pool_kind(team),
        )
        updated = await self._teams.update(
            team_id, name=new_name, picks=None if picks is None else new_picks
        )
        assert updated is not None
        return updated

    async def set_role(self, team_id: int, owner: str, player_id: int, role: Role) -> FantasyTeam:
        """Make one player captain or vice-captain (or neither), moving the role off others."""
        team = await self.get_team(team_id)
        if all(p.player.id != player_id for p in team.picks):
            raise TeamError("invalid", f"Player {player_id} is not in this team.")
        picks = []
        for p in team.picks:
            if p.player.id == player_id:
                picks.append((p.player.id, role))
            elif role is not Role.PLAYER and p.role is role:
                picks.append((p.player.id, Role.PLAYER))
            else:
                picks.append((p.player.id, p.role))
        return await self.update_team(team_id, owner, picks=picks)

    async def delete_team(self, team_id: int, owner: str) -> None:
        team = await self.get_team(team_id)
        if team.owner != owner:
            raise TeamError("forbidden", "Only the team's owner can delete it.")
        await self._teams.delete(team_id)

    # Scoring -----------------------------------------------------------------------------

    async def _scored_matches(
        self, series_id: int, match_id: int | None, cache: dict[int, FixtureDetails | None]
    ) -> list[FixtureDetails]:
        fixtures = await self.series_matches(series_id)
        if match_id is not None:
            fixtures = [f for f in fixtures if f.id == match_id]
        out = []
        for f in fixtures:
            if f.id not in cache:
                cache[f.id] = await self.match_details(f, series_id)
            if cache[f.id] is not None:
                out.append(cache[f.id])
        return out

    def _score_match(self, team: FantasyTeam, details: FixtureDetails) -> MatchScore:
        rows = []
        for pick in team.picks:
            line = details.line_for(pick.player.id)
            stats = line.stats if line else self._rules.stats_type()
            result = calculate_points(
                stats, pick.player.position, self._rules, pick.role, details.fixture.format
            )
            rows.append(PlayerScore(pick, line is not None, result))
        return MatchScore(details.fixture, tuple(rows), sum(r.result.total for r in rows))

    async def team_score(self, team_id: int) -> TeamScore:
        """Points for every started match of the team's series (or its one match)."""
        return await self._team_score(await self.get_team(team_id), {})

    async def _team_score(
        self, team: FantasyTeam, cache: dict[int, FixtureDetails | None]
    ) -> TeamScore:
        matches = [
            self._score_match(team, d)
            for d in await self._scored_matches(team.series_id, team.match_id, cache)
        ]
        per_player: dict[int, float] = {p.player.id: 0.0 for p in team.picks}
        for m in matches:
            for row in m.players:
                per_player[row.pick.player.id] += row.result.total
        return TeamScore(team, tuple(matches), sum(m.total for m in matches), per_player)

    async def leaderboard(self, series_id: int, match_id: int | None = None) -> list[TeamScore]:
        """Every team in the series (or for one match), best first."""
        cache: dict[int, FixtureDetails | None] = {}
        teams = await self.list_teams(series_id=series_id, match_id=match_id)
        if match_id is None:
            teams = [t for t in teams if t.match_id is None]
        scores = [await self._team_score(t, cache) for t in teams]
        return sorted(scores, key=lambda s: -s.total)
