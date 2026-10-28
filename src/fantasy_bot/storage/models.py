"""SQLAlchemy ORM tables."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SquadPlayer(Base):
    """A player in a user's squad. Player details are denormalised to avoid API lookups."""

    __tablename__ = "squad_players"

    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.chat_id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    team_id: Mapped[int] = mapped_column(Integer, index=True)
    team_name: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(16))
    role: Mapped[str] = mapped_column(String(16), default="player")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StatSnapshot(Base):
    """Last stats seen for a player in a fixture; diffing against it drives alerts.

    Persisting it makes alerts idempotent across restarts: a restarted bot never re-sends
    a goal it already announced.
    """

    __tablename__ = "stat_snapshots"

    fixture_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stats: Mapped[dict] = mapped_column(JSON)
    fixture_label: Mapped[str] = mapped_column(String(160), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, index=True
    )


class PoolRow(Base):
    """A user's pool of fantasy teams for a series, or one match of it."""

    __tablename__ = "pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16), default="normal")
    series_id: Mapped[int] = mapped_column(Integer, index=True)
    series_name: Mapped[str] = mapped_column(String(160), default="")
    match_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FantasyTeamRow(Base):
    """A user's fantasy team for a series, or for one match of it when ``match_id`` is set."""

    __tablename__ = "fantasy_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(64))
    series_id: Mapped[int] = mapped_column(Integer, index=True)
    series_name: Mapped[str] = mapped_column(String(160), default="")
    match_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    pool_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    players: Mapped[list[FantasyTeamPlayerRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="FantasyTeamPlayerRow.slot"
    )


class FantasyTeamPlayerRow(Base):
    """A player picked in a fantasy team. Player details are denormalised, like squads."""

    __tablename__ = "fantasy_team_players"

    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fantasy_teams.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, default=0)  # pick order, for display
    name: Mapped[str] = mapped_column(String(128))
    club_id: Mapped[int] = mapped_column(Integer)  # the real team the player plays for
    club_name: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(16))
    role: Mapped[str] = mapped_column(String(16), default="player")


class MatchScorecardRow(Base):
    """A finished match's raw stats, kept so team scores never re-scrape finished games."""

    __tablename__ = "match_scorecards"

    fixture_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, index=True)
    data: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
