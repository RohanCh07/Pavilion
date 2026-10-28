"""CREX scraper: page-state parsing (real, trimmed CREX data) and the HTTP provider."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from fantasy_bot.domain import CricketPosition
from fantasy_bot.providers import ProviderError
from fantasy_bot.providers import crex_parser as parser
from fantasy_bot.providers.crex import CrexProvider

FIXTURES = Path(__file__).parent / "fixtures" / "crex"
TILAK, SANTNER, PHILLIPS, SAMSON = (parser.key_to_id(k) for k in ("15Q", "BR", "MP", "72"))
SEIFERT, ARSHDEEP = parser.key_to_id("JX"), parser.key_to_id("E5")
NZ_IND = parser.key_to_id("12JD")


def state(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf8"))


def as_page(data: dict) -> str:
    """Wrap state the way CREX does: Angular TransferState escaping inside a script tag."""
    body = json.dumps(data)
    for char, escaped in (("&", "&a;"), ('"', "&q;"), ("'", "&s;"), ("<", "&l;"), (">", "&g;")):
        body = body.replace(char, escaped)
    return f'<html><script id="app-root-state" type="application/json">{body}</script></html>'


def scorecard(name="scorecard_12JD.json", key="12JD", squads=True):
    sq = parser.map_squads(state("details_12JD.json")) if squads else None
    return parser.map_scorecard(state(name), key, sq)


# Parsing -----------------------------------------------------------------------------------


def test_extract_state_undoes_transfer_state_escaping():
    data = {"x": 'it\'s <b>&</b> "quoted"'}
    assert parser.extract_state(as_page(data)) == data
    with pytest.raises(ValueError):
        parser.extract_state("<html>no state</html>")


@pytest.mark.parametrize("key", ["0", "Z", "15Q", "12JD", "1DH"])
def test_keys_round_trip(key):
    assert parser.id_to_key(parser.key_to_id(key)) == key


def test_schedule_maps_status_scores_and_kickoff():
    by_key = {parser.id_to_key(f.id): f for f in parser.map_schedule(state("home.json"))}
    nz_ind = by_key["12JD"]
    assert (nz_ind.home_name, nz_ind.away_name, nz_ind.status) == ("New Zealand", "India", "FT")
    assert nz_ind.scoreline == "NZ 180/5 (20.0) · IND 181/6 (19.5) · IND won by 4 wickets"
    assert nz_ind.kickoff == datetime(2026, 10, 24, 7, tzinfo=UTC)
    assert nz_ind.league_name == "India tour of New Zealand 2026"
    assert by_key["13NE"].status == "NS" and by_key["13NE"].scoreline == "PAK vs ENG"
    assert by_key["14YO"].is_live


def test_squads_give_roles_keepers_and_playing_xi():
    squads = parser.map_squads(state("details_12JD.json"))
    assert len(squads.playing_xi) == 22
    assert squads.position_of(SEIFERT) is CricketPosition.WICKET_KEEPER
    assert squads.position_of(SAMSON) is CricketPosition.WICKET_KEEPER
    assert squads.position_of(SANTNER) is CricketPosition.ALL_ROUNDER
    assert squads.position_of(ARSHDEEP) is CricketPosition.BOWLER
    tilak = next(p for p in squads.players if p.id == TILAK)
    assert (tilak.name, tilak.team_name) == ("Tilak Varma", "India")


def test_scorecard_maps_raw_batting_bowling_and_fielding_stats():
    d = scorecard()
    assert d.fixture.scoreline == "NZ 180/5 (20.0) · IND 181/6 (19.5) · India won by 4 wickets"
    assert d.fixture.is_finished and d.fixture.team_ids == {
        parser.key_to_id("R"),
        parser.key_to_id("O"),
    }

    tilak = d.line_for(TILAK).stats
    assert (tilak.runs, tilak.balls_faced, tilak.fours, tilak.sixes) == (51, 26, 6, 1)
    assert tilak.batted and not tilak.out and tilak.catches == 2

    santner = d.line_for(SANTNER).stats  # 4-0-21-4, one of them bowled (Iyer)
    assert (santner.balls_bowled, santner.runs_conceded, santner.maidens) == (24, 21, 0)
    assert (santner.wickets, santner.lbw_bowled) == (4, 1)

    phillips = d.line_for(PHILLIPS).stats  # 70 (43), caught twice in the deep
    assert (phillips.runs, phillips.out, phillips.catches) == (70, True, 2)
    assert all(line.stats.in_xi for line in d.players)
    assert len(d.players) == 22


def test_live_scorecard_includes_team_yet_to_bat():
    d = parser.map_scorecard(state("scorecard_14YO_live.json"), "14YO")
    assert d.fixture.is_live
    batting_second = [ln for ln in d.players if ln.player.team_id == parser.key_to_id("DE")]
    assert len(batting_second) == 11 and all(ln.stats.in_xi for ln in batting_second)
    assert not any(ln.stats.batted for ln in batting_second)


def _one_innings(batting: list[str], bowling: list[str] = ()) -> dict:
    return {
        "match-T1": {"s": 1, "team1": {"fkey": "A", "name": "A"}, "team2": {"fkey": "B"}},
        "getSC4": [{"c": "A", "b": batting, "a": list(bowling), "d": "10/4(30"}],
    }


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("P1.0.3.0.0.1.0.4.F1/-/", {"F1": ("run_outs_direct", 1)}),
        (
            "P1.0.3.0.0.1.0.4.F1.F2/-/",
            {"F1": ("run_outs_assisted", 1), "F2": ("run_outs_assisted", 1)},
        ),
        ("P1.0.3.0.0.1.0.8.BW.WK/-/", {"WK": ("stumpings", 1)}),
        ("P1.0.3.0.0.1.0.3.BW/-/", {"BW": ("catches", 1)}),
        ("P1.0.3.0.0.1.0.5.BW/-/", {"BW": ("lbw_bowled", 1)}),
    ],
)  # fmt: skip
def test_dismissal_codes_credit_the_right_fielders(entry, expected):
    d = parser.map_scorecard(_one_innings([entry]), "T1")
    batter = d.line_for(parser.key_to_id("P1")).stats
    assert batter.out and batter.batted and batter.runs == 0
    for key, (field, value) in expected.items():
        line = d.line_for(parser.key_to_id(key))
        assert getattr(line.stats, field) == value
        assert line.player.team_id == parser.key_to_id("B")  # credited to the fielding side


def test_scorecard_never_reads_points():
    """Only raw stats leave the parser; points are the scoring engine's job."""
    fields = set(scorecard().players[0].stats.to_dict())
    assert not {f for f in fields if "point" in f or "fantasy" in f}


# Provider ----------------------------------------------------------------------------------


def _pages(status_for: dict[str, int] | None = None):
    pages = {
        "/": as_page(state("home.json")),
        "/cricket-live-score/match-updates-12JD/match-scorecard": as_page(
            state("scorecard_12JD.json")
        ),
        "/cricket-live-score/match-updates-12JD/match-details": as_page(state("details_12JD.json")),
    }
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        assert "FantasyPointsBot" in request.headers["user-agent"]
        assert "/api/" not in path and request.url.host == "crex.com"
        if code := (status_for or {}).get(path):
            return httpx.Response(code)
        return httpx.Response(200, text=pages.get(path, "<html>no state</html>"))

    return handler, seen


def _provider(handler) -> CrexProvider:
    client = httpx.AsyncClient(base_url="https://crex.com", transport=httpx.MockTransport(handler))
    provider = CrexProvider(client=client, min_interval=0)
    provider._warm_squads = lambda: None  # tests drive squad loading explicitly
    return provider


async def test_provider_fixture_details_merges_schedule_and_squads():
    handler, seen = _pages()
    provider = _provider(handler)
    day = datetime(2026, 10, 24, tzinfo=UTC).date()
    assert NZ_IND in {f.id for f in await provider.fixtures_on(day)}

    [details] = await provider.fixture_details([NZ_IND])
    assert details.fixture.kickoff == datetime(2026, 10, 24, 7, tzinfo=UTC)  # from home page
    assert details.line_for(SEIFERT).player.position is CricketPosition.WICKET_KEEPER
    # Cached: a second call within the TTL makes no new requests.
    count = len(seen)
    await provider.fixture_details([NZ_IND])
    assert len(seen) == count
    await provider.aclose()


async def test_provider_search_and_last_fixture():
    handler, _ = _pages()
    provider = _provider(handler)
    found = await provider.search_players("Tilak")
    assert [p.name for p in found] == ["Tilak Varma"]
    assert await provider.search_players("ti") == []  # too short
    last = await provider.last_fixture_for_team(found[0].team_id)
    assert last is not None and last.id == NZ_IND
    await provider.aclose()


async def test_provider_series_filter():
    handler, _ = _pages()
    client = httpx.AsyncClient(base_url="https://crex.com", transport=httpx.MockTransport(handler))
    provider = CrexProvider(["2GR"], client=client, min_interval=0)
    provider._warm_squads = lambda: None
    fixtures = await provider._all_fixtures()
    assert {parser.id_to_key(f.id) for f in fixtures} == {"12JD"}
    await provider.aclose()


async def test_provider_raises_on_blocked_page_without_retrying():
    handler, seen = _pages({"/": 403})
    provider = _provider(handler)
    with pytest.raises(ProviderError):
        await provider.fixtures_on(datetime(2026, 10, 24, tzinfo=UTC).date())
    assert seen == ["/"]
    await provider.aclose()


# Series pages -----------------------------------------------------------------------------

NZ_TOUR = parser.key_to_id("2GR")


def test_series_list():
    series = {parser.id_to_key(s.id): s for s in parser.map_series_list(state("series_list.json"))}
    tour = series["2GR"]
    assert (tour.name, tour.status) == ("India tour of New Zealand 2026", "live")
    assert tour.start == datetime(2026, 10, 22, tzinfo=UTC)
    assert series["2MN"].status == "finished"


def test_series_matches_in_order_with_scores():
    matches = parser.map_series_matches(state("series_2GR_matches.json"))
    assert len(matches) == 12  # 5 T20Is, 5 ODIs, 2 Tests
    assert [parser.id_to_key(m.id) for m in matches[:3]] == ["12JC", "12JD", "12JE"]
    first = matches[0]
    assert first.league_id == NZ_TOUR and first.is_finished
    assert first.scoreline == "NZ 225/4 (20.0) · IND 230/6 (19.4) · IND Won by 4 wickets"
    assert matches[2].status == "NS" and matches[2].scoreline == "NZ vs IND"


def test_series_squads_cover_every_format():
    players = {p.id: p for p in parser.map_series_squads(state("series_2GR.json"))}
    assert players[TILAK].position is CricketPosition.ALL_ROUNDER
    assert players[parser.key_to_id("AK")].position is CricketPosition.WICKET_KEEPER  # KL Rahul
    assert players[parser.key_to_id("4I")].name == "Virat Kohli"  # ODI squad only
    assert {p.team_name for p in players.values()} == {"India", "New Zealand"}


def test_schedule_reads_the_renamed_top_matches_list():
    """CREX renamed getLiveMatches to getTopMatches (Oct 2026); both must work."""
    home = state("home.json")
    renamed = {
        ("https://api.goscorer.com/api/v4/getTopMatches" if "getLiveMatches" in k else k): v
        for k, v in home.items()
    }
    assert {f.id for f in parser.map_schedule(renamed)} == {f.id for f in parser.map_schedule(home)}


def test_fixtures_carry_their_format():
    by_key = {parser.id_to_key(f.id): f for f in parser.map_schedule(state("home.json"))}
    assert (by_key["12JD"].format, by_key["13NE"].format, by_key["10MR"].format) == (
        "t20",
        "odi",
        "test",
    )
    assert scorecard().fixture.format == "t20"  # from the match header
    matches = parser.map_series_matches(state("series_2GR_matches.json"))
    assert {m.format for m in matches} == {"t20", "odi", "test"}
