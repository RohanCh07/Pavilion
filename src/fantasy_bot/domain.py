"""Provider-agnostic domain models.

Every data source is mapped into these types before anything else touches the data, so the
scoring engine, tracker and bot never see raw API payloads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class Position(StrEnum):
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    FORWARD = "forward"

    @classmethod
    def parse(cls, raw: str | None) -> Position:
        """Accepts API-Football's long ('Goalkeeper') and short ('G') forms."""
        value = (raw or "").strip().lower()
        for pos in cls:
            if value in (pos.value, pos.value[0]):
                return pos
        return cls.FORWARD  # "Attacker", "F" and unknowns


class CricketPosition(StrEnum):
    BATTER = "batter"
    WICKET_KEEPER = "wicket_keeper"
    ALL_ROUNDER = "all_rounder"
    BOWLER = "bowler"


AnyPosition = Position | CricketPosition


def parse_position(value: str) -> AnyPosition:
    """Rebuild a stored position value; football and cricket values never overlap."""
    try:
        return Position(value)
    except ValueError:
        return CricketPosition(value)


CRICKET_FORMATS = ("t20", "odi", "test")


def cricket_format(raw: str | int | None) -> str:
    """Normalise a source's format label ("T20I", "One Day", "First Class", 2...) to
    "t20", "odi" or "test"; "" when unknown, which scores with the default (T20) rules."""
    value = str(raw or "").strip().lower().replace("-", " ")
    if value in {"2", "t20", "t20i", "t10", "100b", "the hundred"} or "t20" in value:
        return "t20"
    if (
        value in {"1", "odi", "one day", "list a", "youth odi", "odi w"}
        or "odi" in value
        or "one day" in value
    ):
        return "odi"
    if (
        value in {"3", "test", "first class", "youth test", "4 day", "multi day"}
        or "test" in value
        or "first class" in value
    ):
        return "test"
    return ""


class Role(StrEnum):
    PLAYER = "player"
    CAPTAIN = "captain"
    VICE_CAPTAIN = "vice_captain"


# Statuses as reported by API-Football; the mock provider uses the same codes.
LIVE_STATUSES = frozenset({"1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"})
FINISHED_STATUSES = frozenset({"FT", "AET", "PEN"})
DEAD_STATUSES = frozenset({"PST", "CANC", "ABD", "AWD", "WO"})


class _StatsDict:
    """JSON round-tripping shared by every sport's stats, for storing snapshots."""

    __slots__ = ()

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None):
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass(frozen=True, slots=True)
class PlayerStats(_StatsDict):
    """Countable match events for one football player in one fixture."""

    minutes: int = 0
    started: bool = False
    goals: int = 0
    assists: int = 0
    saves: int = 0
    penalties_saved: int = 0
    penalties_missed: int = 0
    own_goals: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    team_conceded: int = 0


@dataclass(frozen=True, slots=True)
class CricketStats(_StatsDict):
    """One cricketer's raw scorecard numbers in one match (all innings summed).

    Only what a scorecard shows: providers never supply fantasy points, the engine
    computes them from these numbers and the ruleset.
    """

    in_xi: bool = False  # named in the playing XI
    batted: bool = False  # came to the crease
    out: bool = False  # dismissed (any mode)
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    balls_bowled: int = 0
    runs_conceded: int = 0
    wickets: int = 0  # bowler's wickets, run outs excluded (as on the scorecard)
    lbw_bowled: int = 0  # of those wickets, how many were LBW or bowled
    maidens: int = 0
    catches: int = 0
    stumpings: int = 0
    run_outs_direct: int = 0  # the only fielder credited
    run_outs_assisted: int = 0  # one of two fielders credited


@dataclass(frozen=True, slots=True)
class Fixture:
    id: int
    league_id: int
    league_name: str
    home_id: int
    home_name: str
    away_id: int
    away_name: str
    kickoff: datetime
    status: str = "NS"
    elapsed: int | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    # For sports scored without goals, e.g. "NZ 180/5 (20.0) · IND 12/0 (1.2)", plus the
    # same split per side ("180/5 (20.0)") and the result line once finished.
    score_text: str | None = None
    home_score: str = ""
    away_score: str = ""
    result: str = ""
    # Cricket match format ("t20", "odi" or "test"; see cricket_format). Picks the ruleset.
    format: str = ""

    @property
    def is_live(self) -> bool:
        return self.status in LIVE_STATUSES

    @property
    def is_finished(self) -> bool:
        return self.status in FINISHED_STATUSES

    @property
    def team_ids(self) -> frozenset[int]:
        return frozenset({self.home_id, self.away_id})

    @property
    def scoreline(self) -> str:
        if self.score_text:
            return self.score_text
        if self.home_goals is None:
            return f"{self.home_name} vs {self.away_name}"
        return f"{self.home_name} {self.home_goals}-{self.away_goals} {self.away_name}"

    def in_tracking_window(
        self,
        now: datetime | None = None,
        before: timedelta = timedelta(minutes=10),
        after: timedelta = timedelta(hours=3),
    ) -> bool:
        """True while the match could be producing points (kickoff - 10m to kickoff + 3h)."""
        if self.is_finished or self.status in DEAD_STATUSES:
            return False
        now = now or datetime.now(UTC)
        return self.is_live or (self.kickoff - before) <= now <= (self.kickoff + after)


@dataclass(frozen=True, slots=True)
class PlayerInfo:
    """A searchable player, as stored in a user's squad."""

    id: int
    name: str
    team_id: int
    team_name: str
    position: AnyPosition


@dataclass(frozen=True, slots=True)
class PlayerLine:
    """One player's stats inside a fixture."""

    player: PlayerInfo
    stats: PlayerStats


@dataclass(frozen=True, slots=True)
class FixtureDetails:
    fixture: Fixture
    players: tuple[PlayerLine, ...] = field(default_factory=tuple)

    def line_for(self, player_id: int) -> PlayerLine | None:
        return next((line for line in self.players if line.player.id == player_id), None)


@dataclass(frozen=True, slots=True)
class Series:
    """A tournament, tour or league: the unit fantasy teams are built for."""

    id: int
    name: str
    short_name: str = ""
    start: datetime | None = None
    end: datetime | None = None
    status: str = "upcoming"  # "upcoming", "live" or "finished"


@dataclass(frozen=True, slots=True)
class TeamPick:
    """One player in a fantasy team, with their captaincy role."""

    player: PlayerInfo
    role: Role = Role.PLAYER


@dataclass(frozen=True, slots=True)
class FantasyTeam:
    """A user's fantasy team for a whole series, or for one match of it (``match_id``)."""

    id: int
    owner: str
    name: str
    series_id: int
    series_name: str
    match_id: int | None
    picks: tuple[TeamPick, ...]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pool_id: int | None = None  # set for teams that belong to a pool


POOL_KINDS = ("normal", "dream")


@dataclass(frozen=True, slots=True)
class Pool:
    """A group of fantasy teams for one series or match, with its own leaderboard.

    "normal" pools have no team rules; "dream" pools use Dream11-style team rules.
    """

    id: int
    owner: str
    name: str
    kind: str
    series_id: int
    series_name: str
    match_id: int | None
    created_at: datetime | None = None
