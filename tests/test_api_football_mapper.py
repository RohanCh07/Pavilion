from datetime import UTC, datetime

from fantasy_bot.domain import Position
from fantasy_bot.providers.api_football_mapper import (
    map_fixture_details,
    map_player_search,
)


def _player(
    pid,
    name,
    pos,
    minutes,
    sub=False,
    goals=None,
    assists=None,
    saves=None,
    yellow=0,
    red=0,
    pen_missed=None,
    pen_saved=None,
):
    return {
        "player": {"id": pid, "name": name},
        "statistics": [
            {
                "games": {"minutes": minutes, "position": pos, "substitute": sub},
                "goals": {"total": goals, "assists": assists, "saves": saves, "conceded": 0},
                "cards": {"yellow": yellow, "red": red},
                "penalty": {"missed": pen_missed, "saved": pen_saved},
            }
        ],
    }


FIXTURE = {
    "fixture": {
        "id": 99,
        "date": "2026-10-21T19:00:00+00:00",
        "status": {"short": "2H", "elapsed": 67},
    },
    "league": {"id": 39, "name": "Premier League"},
    "teams": {"home": {"id": 42, "name": "Arsenal"}, "away": {"id": 49, "name": "Chelsea"}},
    "goals": {"home": 2, "away": 0},
    "events": [
        {"type": "Goal", "detail": "Normal Goal", "player": {"id": 1}},
        {"type": "Goal", "detail": "Own Goal", "player": {"id": 3}},
    ],
    "players": [
        {
            "team": {"id": 42, "name": "Arsenal"},
            "players": [
                _player(1, "B. Saka", "F", 67, goals=1, assists=None),
                _player(2, "D. Raya", "G", 67, saves=3, pen_saved=1),
            ],
        },
        {
            "team": {"id": 49, "name": "Chelsea"},
            "players": [
                _player(3, "L. Colwill", "D", 67, yellow=1),
                _player(4, "N. Jackson", "F", None, sub=True),
            ],
        },
    ],
}


def test_maps_fixture_header():
    f = map_fixture_details(FIXTURE).fixture
    assert (f.id, f.status, f.elapsed, f.home_goals, f.away_goals) == (99, "2H", 67, 2, 0)
    assert f.kickoff == datetime(2026, 10, 21, 19, tzinfo=UTC)
    assert f.is_live and f.team_ids == {42, 49}


def test_maps_player_stats_and_nulls_as_zero():
    d = map_fixture_details(FIXTURE)
    saka = d.line_for(1)
    assert saka.player.position is Position.FORWARD
    assert (saka.stats.goals, saka.stats.assists, saka.stats.started) == (1, 0, True)
    raya = d.line_for(2)
    assert (raya.stats.saves, raya.stats.penalties_saved) == (3, 1)


def test_conceded_comes_from_opponent_score():
    d = map_fixture_details(FIXTURE)
    assert d.line_for(2).stats.team_conceded == 0
    assert d.line_for(3).stats.team_conceded == 2


def test_own_goals_come_from_events():
    d = map_fixture_details(FIXTURE)
    assert d.line_for(3).stats.own_goals == 1
    assert d.line_for(1).stats.own_goals == 0


def test_unused_substitute():
    jackson = map_fixture_details(FIXTURE).line_for(4)
    assert jackson.stats.minutes == 0 and not jackson.stats.started


def test_search_result_mapping():
    item = {
        "player": {"id": 7, "name": "Bukayo Saka"},
        "statistics": [{"team": {"id": 42, "name": "Arsenal"}, "games": {"position": "Attacker"}}],
    }
    info = map_player_search(item)
    assert (info.id, info.team_id, info.position) == (7, 42, Position.FORWARD)
    assert map_player_search({"player": {"id": 8, "name": "x"}, "statistics": []}) is None
