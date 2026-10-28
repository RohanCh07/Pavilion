"""Web API end to end: series browsing, team create/edit/C-VC/delete, scores, leaderboard.

Uses the scripted cricket match, a real SQLite database and FastAPI's test client.
"""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from fantasy_bot.api import build_service, create_app
from fantasy_bot.config import Settings
from fantasy_bot.providers.mock_cricket import FIXTURE_ID, PLAYERS, SERIES_ID, MockCricketProvider
from fantasy_bot.storage import create_engine, init_db, session_factory

KOHLI, PANT, HARDIK, BUMRAH, HEAD, MAXWELL, CUMMINS, ZAMPA = (p.id for p in PLAYERS)
ROHAN = {"X-User-Id": "rohan"}
FRIEND = {"X-User-Id": "friend"}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        telegram_token="", data_provider="mock_cricket", api_football_key="", league_ids=(),
        crex_series=(), season=2026, live_poll_seconds=120, schedule_refresh_seconds=3600,
        scoring_ruleset="dream11_cricket", squad_size=11, database_url="", log_level="INFO",
    )  # fmt: skip


@pytest.fixture
def provider() -> MockCricketProvider:
    return MockCricketProvider()


@pytest.fixture
async def client(tmp_path, settings, provider):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    await init_db(engine)
    service = build_service(settings, provider, session_factory(engine))
    with TestClient(create_app(settings, service)) as c:
        yield c
    await engine.dispose()


def picks(*ids, captain=None, vice=None):
    role = {captain: "captain", vice: "vice_captain"}
    return [{"player_id": i, "role": role.get(i, "player")} for i in ids]


def new_team(client, headers=ROHAN, name="Rohan XI", match_id=None, players=None):
    players = (
        picks(KOHLI, BUMRAH, MAXWELL, captain=KOHLI, vice=BUMRAH) if players is None else players
    )
    body = {"name": name, "series_id": SERIES_ID, "match_id": match_id, "players": players}
    return client.post("/api/teams", json=body, headers=headers)


def finish_match(provider):
    provider.over = 40  # the scripted match is over; stats are complete


def test_browse_series_matches_and_players(client):
    series = client.get("/api/series").json()
    assert series[0]["id"] == SERIES_ID and series[0]["status"] == "upcoming"

    [match] = client.get(f"/api/series/{SERIES_ID}/matches").json()
    assert (match["id"], match["status"], match["home"]["name"]) == (FIXTURE_ID, "NS", "India")

    players = client.get(f"/api/series/{SERIES_ID}/players", params={"q": "MAX"}).json()
    assert [p["name"] for p in players] == ["Glenn Maxwell"]
    assert client.get("/api/rules").json()["captain"] == 2


def test_create_edit_role_and_delete_team(client):
    created = new_team(client)
    assert created.status_code == 201
    team = created.json()
    assert [p["role"] for p in team["players"]] == ["captain", "vice_captain", "player"]

    # Rename and swap the line-up in one edit.
    edited = client.patch(
        f"/api/teams/{team['id']}",
        json={"name": "Renamed", "players": picks(KOHLI, PANT, HEAD, captain=PANT)},
        headers=ROHAN,
    ).json()
    assert edited["name"] == "Renamed"
    assert [(p["name"], p["role"]) for p in edited["players"]] == [
        ("Virat Kohli", "player"),
        ("Rishabh Pant", "captain"),
        ("Travis Head", "player"),
    ]

    # Captaincy moves: making Head captain demotes Pant.
    moved = client.put(
        f"/api/teams/{team['id']}/role",
        json={"player_id": HEAD, "role": "captain"},
        headers=ROHAN,
    ).json()
    assert {p["name"]: p["role"] for p in moved["players"]}["Rishabh Pant"] == "player"

    assert [t["name"] for t in client.get("/api/teams", headers=ROHAN).json()] == ["Renamed"]
    assert client.get("/api/teams", headers=FRIEND).json() == []
    assert client.delete(f"/api/teams/{team['id']}", headers=FRIEND).status_code == 403
    assert client.delete(f"/api/teams/{team['id']}", headers=ROHAN).status_code == 204
    assert client.get(f"/api/teams/{team['id']}").status_code == 404


@pytest.mark.parametrize(
    ("players", "message"),
    [
        (picks(KOHLI, KOHLI), "only be picked once"),
        (picks(KOHLI, PANT, captain=KOHLI) + [{"player_id": PANT, "role": "captain"}], "once"),
        ([{"player_id": 999, "role": "player"}], "not in the squads"),
        ([], "Pick 1-11"),
    ],
)
def test_invalid_teams_are_rejected(client, players, message):
    resp = new_team(client, players=players)
    assert resp.status_code == 422 and message in resp.text


def test_requires_a_user(client):
    assert new_team(client, headers={}).status_code == 401


def test_match_team_locks_at_the_start(client, provider):
    team = new_team(client, match_id=FIXTURE_ID).json()
    provider.over = 4  # match under way
    resp = client.patch(f"/api/teams/{team['id']}", json={"name": "Too late"}, headers=ROHAN)
    assert resp.status_code == 409
    assert new_team(client, match_id=FIXTURE_ID).status_code == 409


def test_team_score_and_leaderboard(client, provider):
    mine = new_team(client).json()  # Kohli (C), Bumrah (VC), Maxwell
    theirs = new_team(
        client, headers=FRIEND, name="Friend XI", players=picks(HEAD, ZAMPA, captain=HEAD)
    ).json()
    assert client.get(f"/api/teams/{mine['id']}/score").json()["points"] == 0  # not started

    finish_match(provider)
    score = client.get(f"/api/teams/{mine['id']}/score").json()
    [match] = score["matches"]
    by_name = {p["name"]: p for p in match["players"]}
    # Kohli 112 base x2, Bumrah 98 base x1.5, Maxwell 79 (see test_cricket for the arithmetic).
    assert by_name["Virat Kohli"]["points"] == 224 and by_name["Virat Kohli"]["multiplier"] == 2
    assert by_name["Jasprit Bumrah"]["points"] == 147
    assert by_name["Glenn Maxwell"]["points"] == 79
    assert score["points"] == match["points"] == 224 + 147 + 79
    assert {p["name"]: p["points"] for p in score["players"]}["Virat Kohli"] == 224

    board = client.get(f"/api/series/{SERIES_ID}/leaderboard").json()
    assert [(r["rank"], r["team_id"]) for r in board] == [(1, mine["id"]), (2, theirs["id"])]

    card = client.get(f"/api/series/{SERIES_ID}/matches/{FIXTURE_ID}/scorecard").json()
    kohli = next(p for p in card["players"] if p["player"]["id"] == KOHLI)
    assert kohli["stats"]["runs"] == 60 and kohli["points"] == 112  # no captaincy here


async def test_finished_scorecards_are_cached(tmp_path, settings):
    """A finished match is read from the database, not the provider, the next time."""
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'cache.db'}")
    await init_db(engine)
    provider = MockCricketProvider()
    service = build_service(settings, provider, session_factory(engine))
    finish_match(provider)
    [fixture] = await service.series_matches(SERIES_ID)
    first = await service.match_details(fixture, SERIES_ID)

    calls = []
    provider.fixture_details = lambda ids: calls.append(ids)  # would break if called
    again = await service.match_details(replace(fixture), SERIES_ID)
    assert calls == [] and again == first
    await engine.dispose()


def test_match_centre_and_rules_text(client):
    [match] = client.get("/api/matches").json()
    assert match["id"] == FIXTURE_ID and match["series_id"] == SERIES_ID
    sections = {s["title"]: s["items"] for s in client.get("/api/rules").json()["sections"]}
    assert "Wicket +30 (not run outs)" in sections["Bowling"]
    assert "Run +1" in sections["Batting"]


def test_rules_list_every_format(client):
    formats = {f["format"]: f for f in client.get("/api/rules").json()["formats"]}
    assert set(formats) == {"t20", "odi", "test"}
    test_bowling = next(s for s in formats["test"]["sections"] if s["title"] == "Bowling")
    assert "Wicket +16 (not run outs)" in test_bowling["items"]
    assert client.get("/api/matches").json()[0]["format"] == "t20"


# Pools ------------------------------------------------------------------------------------


def new_pool(client, kind="normal", teams=None, headers=ROHAN, match_id=None):
    if teams is None:
        teams = [
            {"name": "Rohan", "players": picks(KOHLI, BUMRAH, captain=KOHLI)},
            {"name": "Amit", "players": picks(KOHLI, MAXWELL, HEAD, captain=MAXWELL)},
        ]
    body = {
        "name": "Office pool",
        "type": kind,
        "series_id": SERIES_ID,
        "match_id": match_id,
        "teams": teams,
    }
    return client.post("/api/pools", json=body, headers=headers)


def test_normal_pool_ranks_its_teams_and_allows_shared_players(client, provider):
    created = new_pool(client)
    assert created.status_code == 201
    pool = created.json()
    assert pool["pool"]["type"] == "normal" and pool["pool"]["team_count"] == 2
    pool_id = pool["pool"]["id"]

    # Pool teams live in the pool, not in the user's standalone teams.
    assert client.get("/api/teams", headers=ROHAN).json() == []
    assert [p["name"] for p in client.get("/api/pools", headers=ROHAN).json()] == ["Office pool"]

    finish_match(provider)
    board = client.get(f"/api/pools/{pool_id}").json()["leaderboard"]
    # Rohan: Kohli 112x2 + Bumrah 98 = 322; Amit: Kohli 112 + Maxwell 79x2 + Head 2 = 272
    assert [(r["rank"], r["team"]["name"], r["points"]) for r in board] == [
        (1, "Rohan", 322),
        (2, "Amit", 272),
    ]
    assert board[0]["captain"] == "Virat Kohli"


def test_normal_pool_needs_a_team_and_dream_rules_apply(client):
    assert "at least one team" in new_pool(client, teams=[]).text
    dream = new_pool(client, kind="dream", teams=[])
    assert dream.status_code == 201  # dream pools can start empty
    pool_id = dream.json()["pool"]["id"]
    resp = client.post(
        f"/api/pools/{pool_id}/teams",
        json={"name": "Short", "players": picks(KOHLI, BUMRAH, captain=KOHLI, vice=BUMRAH)},
        headers=ROHAN,
    )
    assert resp.status_code == 422 and "Pick 11 players" in resp.text


def test_only_the_creator_changes_a_pool(client):
    pool_id = new_pool(client).json()["pool"]["id"]
    team = {"name": "Sneaky", "players": picks(HEAD)}
    assert client.post(f"/api/pools/{pool_id}/teams", json=team, headers=FRIEND).status_code == 403
    assert client.post(f"/api/pools/{pool_id}/teams", json=team, headers=ROHAN).status_code == 201
    assert (
        client.patch(f"/api/pools/{pool_id}", json={"name": "Renamed"}, headers=ROHAN).json()[
            "team_count"
        ]
        == 3
    )
    assert client.delete(f"/api/pools/{pool_id}", headers=FRIEND).status_code == 403
    assert client.delete(f"/api/pools/{pool_id}", headers=ROHAN).status_code == 204
    assert client.get(f"/api/pools/{pool_id}").status_code == 404


def test_dream_team_rules():
    from fantasy_bot.domain import CricketPosition, PlayerInfo, TeamPick
    from fantasy_bot.fantasy.service import FantasyService, TeamError

    def team(roles, side_a=6):
        return [
            TeamPick(
                PlayerInfo(i, f"P{i}", 1 if i < side_a else 2, "A" if i < side_a else "B", pos)
            )
            for i, pos in enumerate(roles)
        ]

    WK_, BAT_, AR_, BOWL_ = (CricketPosition.WICKET_KEEPER, CricketPosition.BATTER,
                             CricketPosition.ALL_ROUNDER, CricketPosition.BOWLER)  # fmt: skip
    good = [WK_] + [BAT_] * 4 + [AR_] * 2 + [BOWL_] * 4
    FantasyService._check_dream(team(good), one_match=True)  # valid XI
    with pytest.raises(TeamError, match="wicket-keepers"):
        FantasyService._check_dream(team([BAT_] * 5 + [AR_] * 2 + [BOWL_] * 4), one_match=True)
    with pytest.raises(TeamError, match="at most 7"):
        FantasyService._check_dream(team(good, side_a=9), one_match=True)
    FantasyService._check_dream(team(good, side_a=9), one_match=False)  # series pools: no side cap
