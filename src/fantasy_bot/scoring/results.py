"""Itemised points, shared by every sport's scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreLine:
    key: str
    label: str
    count: int
    points: float


@dataclass(frozen=True, slots=True)
class PointsResult:
    lines: tuple[ScoreLine, ...]
    base: float
    multiplier: float
    total: float

    def by_key(self) -> dict[str, ScoreLine]:
        return {line.key: line for line in self.lines}
