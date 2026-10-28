"""Scoring rules, loaded from TOML so they can change without touching code."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from fantasy_bot.domain import PlayerStats, Position, Role
from fantasy_bot.scoring.cricket import CricketRules

RULESETS_DIR = Path(__file__).parent / "rulesets"

PerPosition = Mapping[Position, float]


def _per_position(raw: Mapping[str, float]) -> PerPosition:
    """Expand {"default": x, "defender": y} into an explicit value for every position."""
    default = raw.get("default", 0)
    unknown = set(raw) - {"default", *Position}
    if unknown:
        raise ValueError(f"Unknown position keys in ruleset: {sorted(unknown)}")
    return MappingProxyType({pos: raw.get(pos.value, default) for pos in Position})


@dataclass(frozen=True, slots=True)
class ScoringRules:
    """Football rules. ``CricketRules`` (scoring/cricket.py) is the cricket counterpart."""

    sport: ClassVar[str] = "football"
    stats_type: ClassVar[type] = PlayerStats
    live_quiet_keys: ClassVar[frozenset[str]] = frozenset()

    name: str
    version: str
    starting_xi: float
    substitute: float
    per_event: Mapping[str, PerPosition]
    clean_sheet_points: PerPosition
    clean_sheet_min_minutes: int
    red_replaces_yellow: bool
    multipliers: Mapping[Role, float] = field(default_factory=dict)

    def points_for(self, stat: str, position: Position) -> float:
        table = self.per_event.get(stat)
        return table[position] if table else 0

    @classmethod
    def from_mapping(cls, data: Mapping) -> ScoringRules:
        appearance = data.get("appearance", {})
        clean = data.get("clean_sheet", {})
        mult = data.get("multipliers", {})
        return cls(
            name=data.get("name", "Custom"),
            version=str(data.get("version", "1")),
            starting_xi=appearance.get("starting_xi", 0),
            substitute=appearance.get("substitute", 0),
            per_event=MappingProxyType(
                {stat: _per_position(v) for stat, v in data.get("per_event", {}).items()}
            ),
            clean_sheet_points=_per_position(clean.get("points", {})),
            clean_sheet_min_minutes=int(clean.get("min_minutes", 60)),
            red_replaces_yellow=bool(data.get("cards", {}).get("red_replaces_yellow", True)),
            multipliers=MappingProxyType(
                {
                    Role.PLAYER: 1.0,
                    Role.CAPTAIN: float(mult.get("captain", 2.0)),
                    Role.VICE_CAPTAIN: float(mult.get("vice_captain", 1.5)),
                }
            ),
        )


@lru_cache(maxsize=8)
def load_rules(name_or_path: str = "dream11_football") -> ScoringRules | CricketRules:
    """Load a bundled ruleset by name, or any TOML file by path.

    The file's top-level ``sport`` key ("football" by default, or "cricket") picks the format.
    """
    path = Path(name_or_path)
    if path.suffix != ".toml":
        path = RULESETS_DIR / f"{name_or_path}.toml"
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    sport = data.get("sport", "football")
    if sport == "cricket":
        rules = CricketRules.from_mapping(data)
        # [formats] names the ruleset for each other format: odi = "dream11_cricket_odi".
        others = {}
        for fmt, ref in (data.get("formats") or {}).items():
            ref_path = Path(ref)
            if ref_path.suffix != ".toml" and not ref_path.is_absolute():
                ref_path = path.parent / f"{ref}.toml"
            with ref_path.open("rb") as fh:
                other = CricketRules.from_mapping(tomllib.load(fh))
            others[fmt.lower()] = replace(other, format=fmt.lower())
        return replace(rules, others=MappingProxyType(others)) if others else rules
    if sport != "football":
        raise ValueError(f"Unknown sport {sport!r} in {path}")
    return ScoringRules.from_mapping(data)
