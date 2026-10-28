from fantasy_bot.domain import PlayerStats, Position
from fantasy_bot.live.events import diff_points


def keys(changes):
    return {c.key: c.points_delta for c in changes}


def test_first_snapshot_reports_everything_scored(rules):
    new = PlayerStats(minutes=30, started=True, goals=1)
    assert keys(diff_points(None, new, Position.FORWARD, rules)) == {"starting_xi": 4, "goals": 6}


def test_unchanged_stats_produce_no_changes(rules):
    s = PlayerStats(minutes=30, started=True, goals=1, team_conceded=1)
    later = PlayerStats(minutes=40, started=True, goals=1, team_conceded=1)
    assert diff_points(s, later, Position.FORWARD, rules) == []


def test_goal_and_assist_deltas(rules):
    old = PlayerStats(minutes=30, started=True, goals=1, team_conceded=1)
    new = PlayerStats(minutes=50, started=True, goals=2, assists=1, team_conceded=1)
    changes = diff_points(old, new, Position.MIDFIELDER, rules)
    assert keys(changes) == {"goals": 8, "assists": 8}
    assert next(c for c in changes if c.key == "goals").count_delta == 1


def test_clean_sheet_gained_then_lost(rules):
    at_59 = PlayerStats(minutes=59, started=True)
    at_60 = PlayerStats(minutes=60, started=True)
    conceded = PlayerStats(minutes=75, started=True, team_conceded=1)
    assert keys(diff_points(at_59, at_60, Position.DEFENDER, rules)) == {"clean_sheet": 8}
    assert keys(diff_points(at_60, conceded, Position.DEFENDER, rules)) == {"clean_sheet": -8}


def test_red_after_yellow_nets_the_difference(rules):
    yellow = PlayerStats(minutes=50, started=True, yellow_cards=1, team_conceded=1)
    red = PlayerStats(minutes=70, started=True, yellow_cards=1, red_cards=1, team_conceded=1)
    assert sum(c.points_delta for c in diff_points(yellow, red, Position.DEFENDER, rules)) == -2
