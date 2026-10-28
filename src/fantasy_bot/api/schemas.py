"""Request and response bodies of the web API (JSON), and their mapping from domain types."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from fantasy_bot.domain import FantasyTeam, Fixture, PlayerInfo, Pool, Role, Series
from fantasy_bot.fantasy import MatchScore, PlayerScore, TeamScore
from fantasy_bot.scoring import PointsResult

# Requests ---------------------------------------------------------------------------------


class PickIn(BaseModel):
    player_id: int
    role: Role = Role.PLAYER


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    series_id: int
    match_id: int | None = Field(None, description="Set for a one-match team; omit for a series")
    players: list[PickIn]


class TeamPatch(BaseModel):
    """Only the fields sent are changed. ``players`` replaces the whole line-up."""

    name: str | None = Field(None, min_length=1, max_length=64)
    players: list[PickIn] | None = None


class PoolTeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    players: list[PickIn]


class PoolIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    type: Literal["normal", "dream"] = Field(
        description='"normal": no team rules. "dream": Dream11-style rules (11 players, C and VC, '
        "role limits, max 7 from one side in a match pool)"
    )
    series_id: int
    match_id: int | None = Field(None, description="Set for a one-match pool; omit for a series")
    teams: list[PoolTeamIn] = Field(default_factory=list, description="Required for normal pools")


class PoolPatch(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class RoleIn(BaseModel):
    player_id: int
    role: Role


# Responses --------------------------------------------------------------------------------


class PlayerOut(BaseModel):
    id: int
    name: str
    team_id: int
    team_name: str
    position: str

    @classmethod
    def of(cls, p: PlayerInfo) -> PlayerOut:
        return cls(
            id=p.id, name=p.name, team_id=p.team_id, team_name=p.team_name,
            position=p.position.value,
        )  # fmt: skip


class SeriesOut(BaseModel):
    id: int
    name: str
    short_name: str
    start: datetime | None
    end: datetime | None
    status: str

    @classmethod
    def of(cls, s: Series) -> SeriesOut:
        return cls(
            id=s.id, name=s.name, short_name=s.short_name, start=s.start, end=s.end,
            status=s.status,
        )  # fmt: skip


class SideOut(BaseModel):
    id: int
    name: str
    score: str = Field(description='e.g. "180/5 (20.0)"; empty before the side bats')


class MatchOut(BaseModel):
    id: int
    series_id: int
    series_name: str
    home: SideOut
    away: SideOut
    start: datetime
    status: str = Field(description="NS (not started), LIVE or FT (finished)")
    format: str = Field(description='Cricket: "t20", "odi", "test" or "" if unknown')
    score: str = Field(description="One-line summary of both sides and the result")
    result: str

    @classmethod
    def of(cls, f: Fixture) -> MatchOut:
        return cls(
            id=f.id,
            series_id=f.league_id,
            series_name=f.league_name,
            home=SideOut(id=f.home_id, name=f.home_name, score=f.home_score),
            away=SideOut(id=f.away_id, name=f.away_name, score=f.away_score),
            start=f.kickoff,
            status=f.status,
            format=f.format,
            score=f.scoreline,
            result=f.result,
        )


class PickOut(PlayerOut):
    role: Role


class TeamOut(BaseModel):
    id: int
    owner: str
    name: str
    series_id: int
    series_name: str
    match_id: int | None
    pool_id: int | None = None
    players: list[PickOut]
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def of(cls, t: FantasyTeam) -> TeamOut:
        return cls(
            id=t.id,
            owner=t.owner,
            name=t.name,
            series_id=t.series_id,
            series_name=t.series_name,
            match_id=t.match_id,
            pool_id=t.pool_id,
            players=[PickOut(**PlayerOut.of(p.player).model_dump(), role=p.role) for p in t.picks],
            created_at=t.created_at,
            updated_at=t.updated_at,
        )


class PoolOut(BaseModel):
    id: int
    owner: str
    name: str
    type: str
    series_id: int
    series_name: str
    match_id: int | None
    team_count: int
    created_at: datetime | None

    @classmethod
    def of(cls, p: Pool, team_count: int) -> PoolOut:
        return cls(
            id=p.id, owner=p.owner, name=p.name, type=p.kind, series_id=p.series_id,
            series_name=p.series_name, match_id=p.match_id, team_count=team_count,
            created_at=p.created_at,
        )  # fmt: skip


class PoolStandingOut(BaseModel):
    rank: int
    team: TeamOut
    points: float
    matches_scored: int
    captain: str | None
    vice_captain: str | None


class PoolDetailOut(BaseModel):
    pool: PoolOut
    leaderboard: list[PoolStandingOut]


class LineOut(BaseModel):
    key: str
    label: str
    count: int
    points: float


class PointsOut(BaseModel):
    base: float
    multiplier: float
    points: float
    lines: list[LineOut]

    @classmethod
    def of(cls, r: PointsResult) -> PointsOut:
        return cls(
            base=r.base,
            multiplier=r.multiplier,
            points=r.total,
            lines=[
                LineOut(key=x.key, label=x.label, count=x.count, points=x.points) for x in r.lines
            ],
        )


class PlayerScoreOut(PointsOut):
    player_id: int
    name: str
    role: Role
    played: bool

    @classmethod
    def of_pick(cls, s: PlayerScore) -> PlayerScoreOut:
        return cls(
            **PointsOut.of(s.result).model_dump(),
            player_id=s.pick.player.id,
            name=s.pick.player.name,
            role=s.pick.role,
            played=s.played,
        )


class MatchScoreOut(BaseModel):
    match: MatchOut
    points: float
    players: list[PlayerScoreOut]

    @classmethod
    def of(cls, m: MatchScore) -> MatchScoreOut:
        return cls(
            match=MatchOut.of(m.fixture),
            points=m.total,
            players=[PlayerScoreOut.of_pick(p) for p in m.players],
        )


class PlayerTotalOut(BaseModel):
    player_id: int
    name: str
    role: Role
    points: float


class TeamScoreOut(BaseModel):
    team: TeamOut
    points: float
    players: list[PlayerTotalOut] = Field(description="Each pick's total over the scored matches")
    matches: list[MatchScoreOut]

    @classmethod
    def of(cls, s: TeamScore) -> TeamScoreOut:
        return cls(
            team=TeamOut.of(s.team),
            points=s.total,
            players=[
                PlayerTotalOut(
                    player_id=p.player.id,
                    name=p.player.name,
                    role=p.role,
                    points=s.player_totals.get(p.player.id, 0),
                )
                for p in s.team.picks
            ],
            matches=[MatchScoreOut.of(m) for m in s.matches],
        )


class LeaderboardRowOut(BaseModel):
    rank: int
    team_id: int
    team_name: str
    owner: str
    points: float
    matches_scored: int


class ScorecardPlayerOut(PointsOut):
    player: PlayerOut
    stats: dict[str, int | bool]


class ScorecardOut(BaseModel):
    """A match's raw stats and the points each player earns (without C/VC multipliers)."""

    match: MatchOut
    players: list[ScorecardPlayerOut]


class RuleSectionOut(BaseModel):
    title: str
    items: list[str]


class FormatRulesOut(BaseModel):
    format: str = Field(description='"t20", "odi" or "test"')
    name: str
    sections: list[RuleSectionOut]


class RulesOut(BaseModel):
    sport: str
    name: str
    version: str
    captain: float
    vice_captain: float
    team_min_players: int
    team_max_players: int
    sections: list[RuleSectionOut] = Field(description="The default (T20) rules, as lines")
    formats: list[FormatRulesOut] = Field(
        default_factory=list, description="Cricket: the rules for each match format"
    )

    @staticmethod
    def formats_of(rules) -> list[FormatRulesOut]:
        return [
            FormatRulesOut(format=r.format, name=r.name, sections=RulesOut.sections_of(r))
            for r in getattr(rules, "all_formats", [])
        ]

    @staticmethod
    def sections_of(rules) -> list[RuleSectionOut]:
        def p(v: float) -> str:
            text = f"{v:g}"
            return f"+{text}" if v > 0 else text

        if getattr(rules, "sport", "") != "cricket":
            return [
                RuleSectionOut(
                    title="Appearance",
                    items=[
                        f"Starting XI {p(rules.starting_xi)}",
                        f"Substitute {p(rules.substitute)}",
                    ],
                )
            ]
        r = rules
        bat = [f"Run {p(r.run)}", f"Four bonus {p(r.four_bonus)}", f"Six bonus {p(r.six_bonus)}"]
        bat += [f"{t.at} runs {p(t.points)}" for t in r.milestones]
        if r.duck:
            bat.append(f"Duck {p(r.duck)}")
        bowl = [f"Wicket {p(r.wicket)} (not run outs)", f"LBW/bowled bonus {p(r.lbw_bowled_bonus)}"]
        bowl += [f"{t.at} wickets {p(t.points)}" for t in r.hauls]
        if r.maiden:
            bowl.append(f"Maiden over {p(r.maiden)}")
        field = [f"Catch {p(r.catch)}", f"Stumping {p(r.stumping)}"]
        if r.catch_bonus:
            field.append(f"{r.catch_bonus.at} catches {p(r.catch_bonus.points)} bonus")
        field += [
            f"Run out (direct) {p(r.run_out_direct)}",
            f"Run out (assist) {p(r.run_out_assisted)}",
        ]
        out = [
            RuleSectionOut(title="Playing XI", items=[f"Named in the XI {p(r.playing_xi)}"]),
            RuleSectionOut(title="Batting", items=bat),
            RuleSectionOut(title="Bowling", items=bowl),
            RuleSectionOut(title="Fielding", items=field),
        ]
        if r.strike_rate.bands:
            out.append(
                RuleSectionOut(
                    title=f"Strike rate (min {r.strike_rate.min_balls} balls)",
                    items=[f"{b.describe()}: {p(b.points)}" for b in r.strike_rate.bands],
                )
            )
        if r.economy.bands:
            out.append(
                RuleSectionOut(
                    title=f"Economy (min {r.economy.min_balls} balls)",
                    items=[f"{b.describe()}: {p(b.points)}" for b in r.economy.bands],
                )
            )
        return out
