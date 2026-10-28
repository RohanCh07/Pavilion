"""All database access goes through here; callers deal only in domain types."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from fantasy_bot.domain import CricketStats, PlayerInfo, PlayerStats, Role, parse_position
from fantasy_bot.storage.models import SquadPlayer, StatSnapshot, User


@dataclass(frozen=True, slots=True)
class SquadMember:
    player: PlayerInfo
    role: Role


Stats = PlayerStats | CricketStats


@dataclass(frozen=True, slots=True)
class Snapshot:
    fixture_id: int
    fixture_label: str
    stats: Stats


class AddResult(Enum):
    ADDED = "added"
    ALREADY_IN_SQUAD = "already"
    SQUAD_FULL = "full"


def _member(row: SquadPlayer) -> SquadMember:
    info = PlayerInfo(
        row.player_id, row.name, row.team_id, row.team_name, parse_position(row.position)
    )
    return SquadMember(info, Role(row.role))


class Repository:
    def __init__(self, sessions: async_sessionmaker, stats_type: type = PlayerStats) -> None:
        """``stats_type`` is the sport's stats class, used to rebuild stored snapshots."""
        self._sessions = sessions
        self._stats = stats_type

    # Users -------------------------------------------------------------------------------

    async def upsert_user(self, chat_id: int, username: str | None) -> None:
        async with self._sessions.begin() as s:
            user = await s.get(User, chat_id)
            if user is None:
                s.add(User(chat_id=chat_id, username=username))
            elif user.username != username:
                user.username = username

    async def set_alerts(self, chat_id: int, enabled: bool) -> None:
        async with self._sessions.begin() as s:
            await s.execute(
                update(User).where(User.chat_id == chat_id).values(alerts_enabled=enabled)
            )

    # Squads ------------------------------------------------------------------------------

    async def get_squad(self, chat_id: int) -> list[SquadMember]:
        async with self._sessions() as s:
            rows = await s.scalars(
                select(SquadPlayer)
                .where(SquadPlayer.chat_id == chat_id)
                .order_by(SquadPlayer.added_at)
            )
            return [_member(r) for r in rows]

    async def add_to_squad(self, chat_id: int, player: PlayerInfo, max_size: int) -> AddResult:
        async with self._sessions.begin() as s:
            if await s.get(SquadPlayer, (chat_id, player.id)):
                return AddResult.ALREADY_IN_SQUAD
            size = await s.scalar(
                select(func.count()).select_from(SquadPlayer).where(SquadPlayer.chat_id == chat_id)
            )
            if size >= max_size:
                return AddResult.SQUAD_FULL
            s.add(
                SquadPlayer(
                    chat_id=chat_id,
                    player_id=player.id,
                    name=player.name,
                    team_id=player.team_id,
                    team_name=player.team_name,
                    position=player.position.value,
                )
            )
            return AddResult.ADDED

    async def remove_from_squad(self, chat_id: int, player_id: int) -> bool:
        async with self._sessions.begin() as s:
            res = await s.execute(
                delete(SquadPlayer).where(
                    SquadPlayer.chat_id == chat_id, SquadPlayer.player_id == player_id
                )
            )
            return res.rowcount > 0

    async def set_role(self, chat_id: int, player_id: int, role: Role) -> bool:
        """Give ``role`` to one player; captain and vice-captain are each held by one player."""
        async with self._sessions.begin() as s:
            target = await s.get(SquadPlayer, (chat_id, player_id))
            if target is None:
                return False
            if role is not Role.PLAYER:
                await s.execute(
                    update(SquadPlayer)
                    .where(SquadPlayer.chat_id == chat_id, SquadPlayer.role == role.value)
                    .values(role=Role.PLAYER.value)
                )
            target.role = role.value
            return True

    # Tracking ----------------------------------------------------------------------------

    async def tracked_team_ids(self) -> set[int]:
        async with self._sessions() as s:
            return set(await s.scalars(select(SquadPlayer.team_id).distinct()))

    async def subscribers(self, player_ids: Iterable[int]) -> dict[int, list[SquadMember]]:
        """chat_id -> that user's squad members among ``player_ids`` (alerts on only)."""
        ids = list(player_ids)
        if not ids:
            return {}
        async with self._sessions() as s:
            rows = await s.scalars(
                select(SquadPlayer)
                .join(User)
                .where(SquadPlayer.player_id.in_(ids), User.alerts_enabled.is_(True))
            )
            out: dict[int, list[SquadMember]] = defaultdict(list)
            for r in rows:
                out[r.chat_id].append(_member(r))
            return dict(out)

    async def get_snapshots(self, fixture_id: int, player_ids: Iterable[int]) -> dict[int, Stats]:
        async with self._sessions() as s:
            rows = await s.scalars(
                select(StatSnapshot).where(
                    StatSnapshot.fixture_id == fixture_id,
                    StatSnapshot.player_id.in_(list(player_ids)),
                )
            )
            return {r.player_id: self._stats.from_dict(r.stats) for r in rows}

    async def save_snapshots(
        self, fixture_id: int, fixture_label: str, stats: Mapping[int, Stats]
    ) -> None:
        if not stats:
            return
        async with self._sessions.begin() as s:
            for pid, st in stats.items():
                await s.merge(
                    StatSnapshot(
                        fixture_id=fixture_id,
                        player_id=pid,
                        stats=st.to_dict(),
                        fixture_label=fixture_label,
                    )
                )

    async def latest_snapshots(self, player_ids: Iterable[int]) -> dict[int, Snapshot]:
        """Each player's most recently updated snapshot (their latest match)."""
        ids = list(player_ids)
        if not ids:
            return {}
        async with self._sessions() as s:
            rows = await s.scalars(
                select(StatSnapshot)
                .where(StatSnapshot.player_id.in_(ids))
                .order_by(StatSnapshot.updated_at)
            )
            # Ordered oldest first, so later rows overwrite earlier ones per player.
            return {
                r.player_id: Snapshot(r.fixture_id, r.fixture_label, self._stats.from_dict(r.stats))
                for r in rows
            }
