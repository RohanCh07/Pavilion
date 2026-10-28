"""Fantasy teams and cached finished scorecards. Callers deal only in domain types."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from fantasy_bot.domain import (
    FantasyTeam,
    Fixture,
    FixtureDetails,
    PlayerInfo,
    PlayerLine,
    Pool,
    Role,
    TeamPick,
    parse_position,
)
from fantasy_bot.storage.models import (
    FantasyTeamPlayerRow,
    FantasyTeamRow,
    MatchScorecardRow,
    PoolRow,
)


def _team(row: FantasyTeamRow) -> FantasyTeam:
    picks = tuple(
        TeamPick(
            PlayerInfo(p.player_id, p.name, p.club_id, p.club_name, parse_position(p.position)),
            Role(p.role),
        )
        for p in row.players
    )
    return FantasyTeam(
        id=row.id,
        owner=row.owner,
        name=row.name,
        series_id=row.series_id,
        series_name=row.series_name,
        match_id=row.match_id,
        picks=picks,
        created_at=row.created_at,
        updated_at=row.updated_at,
        pool_id=row.pool_id,
    )


def _pool(row: PoolRow) -> Pool:
    return Pool(
        id=row.id,
        owner=row.owner,
        name=row.name,
        kind=row.kind,
        series_id=row.series_id,
        series_name=row.series_name,
        match_id=row.match_id,
        created_at=row.created_at,
    )


def _player_rows(picks: Sequence[TeamPick]) -> list[FantasyTeamPlayerRow]:
    return [
        FantasyTeamPlayerRow(
            player_id=p.player.id,
            slot=i,
            name=p.player.name,
            club_id=p.player.team_id,
            club_name=p.player.team_name,
            position=p.player.position.value,
            role=p.role.value,
        )
        for i, p in enumerate(picks)
    ]


def details_to_dict(details: FixtureDetails) -> dict:
    fixture = asdict(details.fixture)
    fixture["kickoff"] = details.fixture.kickoff.isoformat()
    return {
        "fixture": fixture,
        "players": [
            {"player": asdict(ln.player), "stats": ln.stats.to_dict()} for ln in details.players
        ],
    }


def details_from_dict(data: dict, stats_type: type) -> FixtureDetails:
    raw = data["fixture"]
    fixture = Fixture(**{**raw, "kickoff": datetime.fromisoformat(raw["kickoff"])})
    lines = tuple(
        PlayerLine(
            PlayerInfo(**{**p["player"], "position": parse_position(p["player"]["position"])}),
            stats_type.from_dict(p["stats"]),
        )
        for p in data["players"]
    )
    return FixtureDetails(fixture, lines)


class TeamRepository:
    def __init__(self, sessions: async_sessionmaker, stats_type: type) -> None:
        """``stats_type`` is the sport's stats class, used to rebuild cached scorecards."""
        self._sessions = sessions
        self._stats = stats_type

    # Teams -------------------------------------------------------------------------------

    async def create(
        self,
        owner: str,
        name: str,
        series_id: int,
        series_name: str,
        match_id: int | None,
        picks: Sequence[TeamPick],
        pool_id: int | None = None,
    ) -> FantasyTeam:
        async with self._sessions.begin() as s:
            row = FantasyTeamRow(
                owner=owner,
                name=name,
                series_id=series_id,
                series_name=series_name,
                match_id=match_id,
                pool_id=pool_id,
                players=_player_rows(picks),
            )
            s.add(row)
            await s.flush()
            await s.refresh(row, ["players"])
            return _team(row)

    async def get(self, team_id: int) -> FantasyTeam | None:
        async with self._sessions() as s:
            row = await s.get(FantasyTeamRow, team_id)
            return _team(row) if row else None

    async def find(
        self,
        *,
        owner: str | None = None,
        series_id: int | None = None,
        match_id: int | None = None,
        pool_id: int | None = None,
        in_pool: bool | None = False,
    ) -> list[FantasyTeam]:
        """Teams matching the filters. By default only teams outside pools (``in_pool=False``);
        pass ``pool_id`` for one pool's teams, or ``in_pool=None`` for every team."""
        query = select(FantasyTeamRow).order_by(FantasyTeamRow.id)
        if pool_id is not None:
            query = query.where(FantasyTeamRow.pool_id == pool_id)
        elif in_pool is False:
            query = query.where(FantasyTeamRow.pool_id.is_(None))
        elif in_pool is True:
            query = query.where(FantasyTeamRow.pool_id.is_not(None))
        if owner is not None:
            query = query.where(FantasyTeamRow.owner == owner)
        if series_id is not None:
            query = query.where(FantasyTeamRow.series_id == series_id)
        if match_id is not None:
            query = query.where(FantasyTeamRow.match_id == match_id)
        async with self._sessions() as s:
            return [_team(r) for r in await s.scalars(query)]

    async def update(
        self, team_id: int, *, name: str | None = None, picks: Sequence[TeamPick] | None = None
    ) -> FantasyTeam | None:
        async with self._sessions.begin() as s:
            row = await s.get(FantasyTeamRow, team_id)
            if row is None:
                return None
            if name is not None:
                row.name = name
            if picks is not None:
                row.players.clear()
                await s.flush()  # delete the old picks before re-adding the same player ids
                row.players.extend(_player_rows(picks))
            row.updated_at = datetime.now(UTC)
            await s.flush()
            await s.refresh(row, ["players"])
            return _team(row)

    async def delete(self, team_id: int) -> bool:
        async with self._sessions.begin() as s:
            row = await s.get(FantasyTeamRow, team_id)
            if row is None:
                return False
            await s.delete(row)
            return True

    # Pools -------------------------------------------------------------------------------

    async def create_pool(
        self,
        owner: str,
        name: str,
        kind: str,
        series_id: int,
        series_name: str,
        match_id: int | None,
    ) -> Pool:
        async with self._sessions.begin() as s:
            row = PoolRow(
                owner=owner,
                name=name,
                kind=kind,
                series_id=series_id,
                series_name=series_name,
                match_id=match_id,
            )
            s.add(row)
            await s.flush()
            return _pool(row)

    async def get_pool(self, pool_id: int) -> Pool | None:
        async with self._sessions() as s:
            row = await s.get(PoolRow, pool_id)
            return _pool(row) if row else None

    async def find_pools(self, owner: str) -> list[Pool]:
        async with self._sessions() as s:
            rows = await s.scalars(
                select(PoolRow).where(PoolRow.owner == owner).order_by(PoolRow.id.desc())
            )
            return [_pool(r) for r in rows]

    async def rename_pool(self, pool_id: int, name: str) -> Pool | None:
        async with self._sessions.begin() as s:
            row = await s.get(PoolRow, pool_id)
            if row is None:
                return None
            row.name = name
            return _pool(row)

    async def delete_pool(self, pool_id: int) -> None:
        """Delete a pool and its teams."""
        async with self._sessions.begin() as s:
            for team in await s.scalars(
                select(FantasyTeamRow).where(FantasyTeamRow.pool_id == pool_id)
            ):
                await s.delete(team)
            row = await s.get(PoolRow, pool_id)
            if row is not None:
                await s.delete(row)

    async def pool_team_counts(self, pool_ids: Sequence[int]) -> dict[int, int]:
        if not pool_ids:
            return {}
        async with self._sessions() as s:
            rows = await s.execute(
                select(FantasyTeamRow.pool_id, func.count())
                .where(FantasyTeamRow.pool_id.in_(pool_ids))
                .group_by(FantasyTeamRow.pool_id)
            )
            return {pid: n for pid, n in rows}

    # Finished scorecards -----------------------------------------------------------------

    async def get_scorecards(self, fixture_ids: Sequence[int]) -> dict[int, FixtureDetails]:
        if not fixture_ids:
            return {}
        async with self._sessions() as s:
            rows = await s.scalars(
                select(MatchScorecardRow).where(MatchScorecardRow.fixture_id.in_(fixture_ids))
            )
            return {r.fixture_id: details_from_dict(r.data, self._stats) for r in rows}

    async def save_scorecard(self, series_id: int, details: FixtureDetails) -> None:
        async with self._sessions.begin() as s:
            await s.merge(
                MatchScorecardRow(
                    fixture_id=details.fixture.id,
                    series_id=series_id,
                    data=details_to_dict(details),
                )
            )
