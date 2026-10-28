"""Pure scoring: (stats, position, rules, role) -> itemised points. No I/O, no Telegram.

Football is scored here; cricket lives in ``cricket.py``. ``calculate_points`` picks the one
that matches the loaded ruleset, so callers never need to know the sport.
"""

from __future__ import annotations

from fantasy_bot.domain import AnyPosition, CricketStats, PlayerStats, Position, Role
from fantasy_bot.scoring.cricket import CricketRules, calculate_cricket
from fantasy_bot.scoring.results import PointsResult, ScoreLine
from fantasy_bot.scoring.rules import ScoringRules

Rules = ScoringRules | CricketRules

# Display labels for each countable stat, in the order they appear in a breakdown.
STAT_LABELS: dict[str, str] = {
    "goals": "Goals",
    "assists": "Assists",
    "saves": "Saves",
    "penalties_saved": "Penalty saves",
    "penalties_missed": "Penalty misses",
    "own_goals": "Own goals",
    "yellow_cards": "Yellow card",
    "red_cards": "Red card",
}


def has_clean_sheet(stats: PlayerStats, rules: ScoringRules) -> bool:
    # Approximation: uses the team's goals conceded, not only those while the player was on.
    return stats.minutes >= rules.clean_sheet_min_minutes and stats.team_conceded == 0


def calculate_points(
    stats: PlayerStats | CricketStats,
    position: AnyPosition,
    rules: Rules,
    role: Role = Role.PLAYER,
    fmt: str = "",
) -> PointsResult:
    """Itemised points for one player in one match, for whichever sport ``rules`` is.

    ``fmt`` is the match's format (``Fixture.format``); cricket uses that format's rules.
    """
    if isinstance(rules, CricketRules):
        return calculate_cricket(stats, position, rules.for_format(fmt), role)
    return calculate_football(stats, position, rules, role)


def calculate_football(
    stats: PlayerStats,
    position: Position,
    rules: ScoringRules,
    role: Role = Role.PLAYER,
) -> PointsResult:
    lines: list[ScoreLine] = []

    if stats.minutes > 0:
        if stats.started:
            lines.append(ScoreLine("starting_xi", "Starting XI", 1, rules.starting_xi))
        else:
            lines.append(ScoreLine("substitute", "Came off the bench", 1, rules.substitute))

    for key, label in STAT_LABELS.items():
        count = getattr(stats, key)
        if key == "yellow_cards" and stats.red_cards and rules.red_replaces_yellow:
            continue
        per = rules.points_for(key, position)
        if count and per:
            lines.append(ScoreLine(key, label, count, count * per))

    if has_clean_sheet(stats, rules):
        cs = rules.clean_sheet_points[position]
        if cs:
            lines.append(ScoreLine("clean_sheet", "Clean sheet", 1, cs))

    base = sum(line.points for line in lines)
    multiplier = rules.multipliers.get(role, 1.0)
    return PointsResult(tuple(lines), base, multiplier, base * multiplier)
