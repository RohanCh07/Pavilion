"""Cricket scoring: rules loaded from TOML and a pure (stats, position, rules, role) -> points.

Providers only ever supply raw scorecard numbers (``CricketStats``); every point, bonus and
penalty is decided here from the ruleset, so changing the rules never touches a scraper.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar

from fantasy_bot.domain import AnyPosition, CricketPosition, CricketStats, Role
from fantasy_bot.scoring.results import PointsResult, ScoreLine


@dataclass(frozen=True, slots=True)
class Band:
    """A points band over a rate. Bounds are optional: min/max inclusive, above/below strict."""

    points: float
    min: float | None = None
    max: float | None = None
    above: float | None = None
    below: float | None = None

    def contains(self, value: float) -> bool:
        return (
            (self.min is None or value >= self.min)
            and (self.max is None or value <= self.max)
            and (self.above is None or value > self.above)
            and (self.below is None or value < self.below)
        )

    def describe(self) -> str:
        """Human form of the bounds, e.g. ">150 and ≤170"."""
        parts = [
            f"{sign}{bound:g}"
            for sign, bound in (
                ("≥", self.min),
                (">", self.above),
                ("≤", self.max),
                ("<", self.below),
            )
            if bound is not None
        ]
        return " and ".join(parts)


@dataclass(frozen=True, slots=True)
class RateRule:
    """Strike-rate or economy bands, applied once a player has faced/bowled ``min_balls``."""

    min_balls: int = 0
    bands: tuple[Band, ...] = ()
    exempt: frozenset[CricketPosition] = frozenset()

    def points(self, value: float) -> float:
        return next((b.points for b in self.bands if b.contains(value)), 0)


@dataclass(frozen=True, slots=True)
class Threshold:
    at: int  # runs for a milestone, wickets for a haul
    points: float


def _positions(raw: Iterable[str]) -> frozenset[CricketPosition]:
    return frozenset(CricketPosition(p) for p in raw)


def _bands(raw: Sequence[Mapping]) -> tuple[Band, ...]:
    allowed = {"points", "min", "max", "above", "below"}
    for band in raw:
        if unknown := set(band) - allowed:
            raise ValueError(f"Unknown band keys in ruleset: {sorted(unknown)}")
    return tuple(Band(**band) for band in raw)


def _thresholds(raw: Sequence[Mapping], key: str) -> tuple[Threshold, ...]:
    return tuple(sorted((Threshold(int(t[key]), t["points"]) for t in raw), key=lambda t: t.at))


def _reached(thresholds: Sequence[Threshold], value: int, cumulative: bool) -> list[Threshold]:
    hit = [t for t in thresholds if value >= t.at]
    return hit if cumulative else hit[-1:]


@dataclass(frozen=True, slots=True)
class CricketRules:
    sport: ClassVar[str] = "cricket"
    stats_type: ClassVar[type] = CricketStats
    live_quiet_keys: ClassVar[frozenset[str]] = frozenset({"strike_rate", "economy"})

    name: str
    version: str
    playing_xi: float
    run: float
    four_bonus: float
    six_bonus: float
    duck: float
    duck_exempt: frozenset[CricketPosition]
    milestones: tuple[Threshold, ...]
    milestones_cumulative: bool
    wicket: float
    lbw_bowled_bonus: float
    maiden: float
    hauls: tuple[Threshold, ...]
    hauls_cumulative: bool
    catch: float
    catch_bonus: Threshold | None
    stumping: float
    run_out_direct: float
    run_out_assisted: float
    strike_rate: RateRule
    economy: RateRule
    multipliers: Mapping[Role, float] = field(default_factory=dict)
    format: str = "t20"  # the format these rules are for
    # Rules for the other formats ("odi", "test"), filled in by load_rules from [formats].
    others: Mapping[str, CricketRules] = field(default_factory=dict)

    def for_format(self, fmt: str) -> CricketRules:
        """The rules for a match format; these rules when the format is unknown."""
        if not fmt or fmt == self.format:
            return self
        return self.others.get(fmt, self)

    @property
    def all_formats(self) -> list[CricketRules]:
        return [self, *self.others.values()]

    @classmethod
    def from_mapping(cls, data: Mapping) -> CricketRules:
        bat, bowl = data.get("batting", {}), data.get("bowling", {})
        fld, mult = data.get("fielding", {}), data.get("multipliers", {})
        sr, eco = data.get("strike_rate", {}), data.get("economy", {})
        bonus = fld.get("catch_bonus")
        return cls(
            name=data.get("name", "Custom cricket"),
            version=str(data.get("version", "1")),
            playing_xi=data.get("appearance", {}).get("playing_xi", 0),
            run=bat.get("run", 0),
            four_bonus=bat.get("four_bonus", 0),
            six_bonus=bat.get("six_bonus", 0),
            duck=bat.get("duck", 0),
            duck_exempt=_positions(bat.get("duck_exempt", ())),
            milestones=_thresholds(bat.get("milestones", ()), "runs"),
            milestones_cumulative=bool(bat.get("milestones_cumulative", False)),
            wicket=bowl.get("wicket", 0),
            lbw_bowled_bonus=bowl.get("lbw_bowled_bonus", 0),
            maiden=bowl.get("maiden", 0),
            hauls=_thresholds(bowl.get("hauls", ()), "wickets"),
            hauls_cumulative=bool(bowl.get("hauls_cumulative", False)),
            catch=fld.get("catch", 0),
            catch_bonus=Threshold(int(bonus["catches"]), bonus["points"]) if bonus else None,
            stumping=fld.get("stumping", 0),
            run_out_direct=fld.get("run_out_direct", 0),
            run_out_assisted=fld.get("run_out_assisted", 0),
            strike_rate=RateRule(
                int(sr.get("min_balls", 0)),
                _bands(sr.get("bands", ())),
                _positions(sr.get("exempt", ())),
            ),
            economy=RateRule(int(eco.get("min_balls", 0)), _bands(eco.get("bands", ()))),
            multipliers=MappingProxyType(
                {
                    Role.PLAYER: 1.0,
                    Role.CAPTAIN: float(mult.get("captain", 2.0)),
                    Role.VICE_CAPTAIN: float(mult.get("vice_captain", 1.5)),
                }
            ),
            format=str(data.get("format", "t20")).lower(),
        )


MILESTONE_NAMES = {50: "Half-century bonus", 100: "Century bonus"}


def _overs(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def calculate_cricket(
    stats: CricketStats,
    position: AnyPosition,
    rules: CricketRules,
    role: Role = Role.PLAYER,
) -> PointsResult:
    if not isinstance(position, CricketPosition):
        position = CricketPosition.BATTER
    lines: list[ScoreLine] = []

    def add(key: str, label: str, count: int, per: float) -> None:
        if count and per:
            lines.append(ScoreLine(key, label, count, count * per))

    add("playing_xi", "Playing XI", int(stats.in_xi), rules.playing_xi)

    # Batting
    add("runs", "Runs", stats.runs, rules.run)
    add("fours", "Boundary bonus", stats.fours, rules.four_bonus)
    add("sixes", "Six bonus", stats.sixes, rules.six_bonus)
    reached = _reached(rules.milestones, stats.runs, rules.milestones_cumulative)
    if reached:
        top = reached[-1].at
        label = MILESTONE_NAMES.get(top, f"{top}-run bonus")
        lines.append(ScoreLine("milestone", label, 1, sum(t.points for t in reached)))
    if stats.out and stats.runs == 0 and position not in rules.duck_exempt:
        add("duck", "Duck", 1, rules.duck)
    sr_rule = rules.strike_rate
    if stats.balls_faced >= max(sr_rule.min_balls, 1) and position not in sr_rule.exempt:
        sr = stats.runs * 100 / stats.balls_faced
        add("strike_rate", f"Strike rate {sr:.1f}", 1, sr_rule.points(sr))

    # Bowling
    add("wickets", "Wickets", stats.wickets, rules.wicket)
    add("lbw_bowled", "LBW/bowled bonus", stats.lbw_bowled, rules.lbw_bowled_bonus)
    hauls = _reached(rules.hauls, stats.wickets, rules.hauls_cumulative)
    if hauls:
        lines.append(
            ScoreLine(
                "wicket_haul", f"{hauls[-1].at}-wicket bonus", 1, sum(t.points for t in hauls)
            )
        )
    add("maidens", "Maiden overs", stats.maidens, rules.maiden)
    eco_rule = rules.economy
    if stats.balls_bowled >= max(eco_rule.min_balls, 1):
        eco = stats.runs_conceded * 6 / stats.balls_bowled
        add(
            "economy",
            f"Economy {eco:.2f} ({_overs(stats.balls_bowled)} ov)",
            1,
            eco_rule.points(eco),
        )

    # Fielding
    add("catches", "Catches", stats.catches, rules.catch)
    if rules.catch_bonus and stats.catches >= rules.catch_bonus.at:
        add("catch_bonus", f"{rules.catch_bonus.at}-catch bonus", 1, rules.catch_bonus.points)
    add("stumpings", "Stumpings", stats.stumpings, rules.stumping)
    add("run_outs_direct", "Run out (direct hit)", stats.run_outs_direct, rules.run_out_direct)
    add("run_outs_assisted", "Run out (assist)", stats.run_outs_assisted, rules.run_out_assisted)

    base = sum(line.points for line in lines)
    multiplier = rules.multipliers.get(role, 1.0)
    return PointsResult(tuple(lines), base, multiplier, base * multiplier)
