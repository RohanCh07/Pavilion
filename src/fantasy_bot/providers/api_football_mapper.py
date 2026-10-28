"""Pure functions mapping API-Football v3 JSON into domain models."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from fantasy_bot.domain import (
    Fixture,
    FixtureDetails,
    PlayerInfo,
    PlayerLine,
    PlayerStats,
    Position,
)

Json = dict[str, Any]


def _n(value: Any) -> int:
    """API-Football uses null for zero."""
    return int(value or 0)


def map_fixture(item: Json) -> Fixture:
    fx, league, teams, goals = item["fixture"], item["league"], item["teams"], item["goals"]
    return Fixture(
        id=fx["id"],
        league_id=league["id"],
        league_name=league.get("name", ""),
        home_id=teams["home"]["id"],
        home_name=teams["home"]["name"],
        away_id=teams["away"]["id"],
        away_name=teams["away"]["name"],
        kickoff=datetime.fromisoformat(fx["date"]),
        status=fx["status"]["short"],
        elapsed=fx["status"].get("elapsed"),
        home_goals=goals.get("home"),
        away_goals=goals.get("away"),
    )


def _own_goals(events: list[Json]) -> Counter[int]:
    """Own goals only appear in the events feed, keyed by the player who scored them."""
    return Counter(
        e["player"]["id"]
        for e in events
        if e.get("type") == "Goal"
        and e.get("detail") == "Own Goal"
        and e.get("player", {}).get("id")
    )


def map_fixture_details(item: Json) -> FixtureDetails:
    """Map one entry from ``GET /fixtures?ids=...`` (which embeds events and players)."""
    fixture = map_fixture(item)
    own_goals = _own_goals(item.get("events") or [])
    conceded = {fixture.home_id: _n(fixture.away_goals), fixture.away_id: _n(fixture.home_goals)}

    lines: list[PlayerLine] = []
    for team_block in item.get("players") or []:
        team = team_block["team"]
        for entry in team_block.get("players") or []:
            pid = entry["player"]["id"]
            s = (entry.get("statistics") or [{}])[0]
            games, goals = s.get("games") or {}, s.get("goals") or {}
            cards, penalty = s.get("cards") or {}, s.get("penalty") or {}
            minutes = _n(games.get("minutes"))
            info = PlayerInfo(
                id=pid,
                name=entry["player"]["name"],
                team_id=team["id"],
                team_name=team["name"],
                position=Position.parse(games.get("position")),
            )
            stats = PlayerStats(
                minutes=minutes,
                started=minutes > 0 and not games.get("substitute", False),
                goals=_n(goals.get("total")),
                assists=_n(goals.get("assists")),
                saves=_n(goals.get("saves")),
                penalties_saved=_n(penalty.get("saved")),
                penalties_missed=_n(penalty.get("missed")),
                own_goals=own_goals.get(pid, 0),
                yellow_cards=_n(cards.get("yellow")),
                red_cards=_n(cards.get("red")),
                team_conceded=conceded.get(team["id"], 0),
            )
            lines.append(PlayerLine(info, stats))
    return FixtureDetails(fixture, tuple(lines))


def map_player_search(item: Json) -> PlayerInfo | None:
    """Map one entry from ``GET /players?search=...``; None if it has no club stats."""
    stats = item.get("statistics") or []
    if not stats or not (stats[0].get("team") or {}).get("id"):
        return None
    s = stats[0]
    return PlayerInfo(
        id=item["player"]["id"],
        name=item["player"]["name"],
        team_id=s["team"]["id"],
        team_name=s["team"]["name"],
        position=Position.parse((s.get("games") or {}).get("position")),
    )
