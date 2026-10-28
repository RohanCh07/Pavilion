"""Turn two stat snapshots into the point changes worth announcing."""

from __future__ import annotations

from dataclasses import dataclass

from fantasy_bot.domain import AnyPosition, CricketStats, PlayerStats
from fantasy_bot.scoring import Rules, calculate_points

Stats = PlayerStats | CricketStats


@dataclass(frozen=True, slots=True)
class PointChange:
    key: str  # score line key, e.g. "goals", "clean_sheet"
    label: str
    count_delta: int
    points_delta: float  # before captain / vice-captain multiplier


def diff_points(
    old: Stats | None, new: Stats, position: AnyPosition, rules: Rules, fmt: str = ""
) -> list[PointChange]:
    """Changes between two snapshots, derived from the score lines so any rule is covered.

    Works off scored lines rather than raw stats, so a stat that earns no points for this
    position (a defender's saves) produces no alert, and losing a clean sheet does.
    Lines in ``rules.live_quiet_keys`` (cricket's strike rate and economy, which swing every
    ball) never alert; they still count in totals and the full-time summary.
    """
    before = calculate_points(old or rules.stats_type(), position, rules, fmt=fmt).by_key()
    after = calculate_points(new, position, rules, fmt=fmt).by_key()
    changes = []
    for key in dict.fromkeys([*after, *before]):  # stable order, new lines first
        if key in rules.live_quiet_keys:
            continue
        a, b = after.get(key), before.get(key)
        pts = (a.points if a else 0) - (b.points if b else 0)
        if pts:
            label = (a or b).label
            changes.append(
                PointChange(key, label, (a.count if a else 0) - (b.count if b else 0), pts)
            )
    return changes
