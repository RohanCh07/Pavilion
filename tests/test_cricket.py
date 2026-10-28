"""Cricket scoring rules, config checks, and a full scripted match through the tracker."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from conftest import FakeNotifier
from fantasy_bot.config import ConfigError, Settings
from fantasy_bot.domain import CricketPosition, CricketStats, Role
from fantasy_bot.live.events import diff_points
from fantasy_bot.live.tracker import LiveTracker
from fantasy_bot.messages import rules_text
from fantasy_bot.providers.mock_cricket import PLAYERS, MockCricketProvider
from fantasy_bot.scoring import CricketRules, calculate_points, load_rules
from fantasy_bot.storage import Repository, create_engine, init_db, session_factory

BAT, BOWL, AR, WK = (
    CricketPosition.BATTER,
    CricketPosition.BOWLER,
    CricketPosition.ALL_ROUNDER,
    CricketPosition.WICKET_KEEPER,
)


@pytest.fixture
def crules() -> CricketRules:
    return load_rules("dream11_cricket")


def points(stats, position, rules, role=Role.PLAYER):
    return calculate_points(stats, position, rules, role)


# Scoring ----------------------------------------------------------------------------------


def test_real_scorecard_lines(crules):
    # Mitchell Santner, NZ v IND 2026: 4 (5) and 4-0-21-4 with one bowled.
    santner = CricketStats(
        in_xi=True, batted=True, runs=4, balls_faced=5, balls_bowled=24, runs_conceded=21,
        wickets=4, lbw_bowled=1,
    )  # fmt: skip
    r = points(santner, AR, crules)
    # 4 XI + 4 runs + 120 wickets + 8 bowled + 8 four-wicket haul + 4 economy 5.25
    assert r.total == 148
    assert r.by_key()["economy"].points == 4

    # Glenn Phillips: 70 (43), 4x4, 4x6, out, two catches.
    phillips = CricketStats(
        in_xi=True, batted=True, out=True, runs=70, balls_faced=43, fours=4, sixes=4, catches=2
    )
    r = points(phillips, AR, crules)
    # 4 + 70 + 16 + 24 + 8 (fifty) + 4 (SR 162.8) + 16 catches
    assert r.total == 142


def test_milestones_count_highest_only_unless_cumulative(crules):
    hundred = CricketStats(batted=True, runs=100, balls_faced=200)
    assert points(hundred, BAT, crules).by_key()["milestone"].points == 16
    cumulative = replace(crules, milestones_cumulative=True)
    assert points(hundred, BAT, cumulative).by_key()["milestone"].points == 4 + 8 + 12 + 16


def test_duck_applies_except_to_bowlers(crules):
    duck = CricketStats(batted=True, out=True, balls_faced=3)
    assert points(duck, BAT, crules).by_key()["duck"].points == -2
    assert points(duck, WK, crules).by_key()["duck"].points == -2
    assert "duck" not in points(duck, BOWL, crules).by_key()
    not_out = replace(duck, out=False)
    assert "duck" not in points(not_out, BAT, crules).by_key()


@pytest.mark.parametrize(
    ("runs", "balls", "expected"),
    [(18, 10, 6), (17, 10, 4), (15, 10, 2), (13, 10, 2), (7, 10, -2), (5, 10, -4), (4, 10, -6),
     (10, 10, None), (30, 9, None)],  # None: no line (a 0-point band, or too few balls)
)  # fmt: skip
def test_strike_rate_bands(crules, runs, balls, expected):
    stats = CricketStats(batted=True, runs=runs, balls_faced=balls)
    line = points(stats, BAT, crules).by_key().get("strike_rate")
    assert (line.points if line else None) == expected
    assert "strike_rate" not in points(stats, BOWL, crules).by_key()  # bowlers exempt


@pytest.mark.parametrize(
    ("conceded", "balls", "expected"),
    [(19, 24, 6), (20, 24, 4), (28, 24, 2), (40, 24, -2), (46, 24, -4), (49, 24, -6),
     (32, 24, None), (30, 11, None)],
)  # fmt: skip
def test_economy_bands(crules, conceded, balls, expected):
    stats = CricketStats(balls_bowled=balls, runs_conceded=conceded)
    line = points(stats, BOWL, crules).by_key().get("economy")
    assert (line.points if line else None) == expected


def test_fielding_and_captaincy(crules):
    fielder = CricketStats(
        in_xi=True, catches=3, stumpings=1, run_outs_direct=1, run_outs_assisted=1
    )
    r = points(fielder, WK, crules, Role.VICE_CAPTAIN)
    # 4 + 24 catches + 4 bonus + 12 stumping + 12 direct + 6 assist = 62, x1.5
    assert (r.base, r.total) == (62, 93)


def test_rate_lines_never_alert_live(crules):
    before = CricketStats(batted=True, runs=14, balls_faced=10)
    after = CricketStats(batted=True, runs=14, balls_faced=12)  # SR 140 -> 116.7: +2 -> 0
    assert diff_points(before, after, BAT, crules) == []
    assert points(after, BAT, crules).total != points(before, BAT, crules).total


def test_cricket_rules_text_lists_bands(crules):
    text = rules_text(crules)
    assert "Dream11 Cricket" in text and "&gt;170: +6" in text and "(highest only)" in text


# Config -----------------------------------------------------------------------------------


def _settings(provider: str, ruleset: str = "") -> Settings:
    sport = {"crex": "cricket", "mock_cricket": "cricket"}.get(provider, "football")
    return Settings(
        telegram_token="t", data_provider=provider, api_football_key="", league_ids=(39,),
        crex_series=(), season=2026, live_poll_seconds=120, schedule_refresh_seconds=3600,
        scoring_ruleset=ruleset or f"dream11_{sport}", squad_size=11, database_url="",
        log_level="INFO",
    )  # fmt: skip


def test_settings_pick_sport_and_reject_mismatched_ruleset():
    crex = _settings("crex")
    crex.validate()  # no API key needed
    crex.check_ruleset()
    assert crex.sport == "cricket"
    with pytest.raises(ConfigError, match="football ruleset"):
        _settings("crex", "dream11_football").check_ruleset()
    with pytest.raises(ConfigError, match="DATA_PROVIDER"):
        _settings("sofascore").validate()


def test_default_ruleset_follows_provider(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("DATA_PROVIDER", "crex")
    monkeypatch.delenv("SCORING_RULESET", raising=False)
    monkeypatch.setenv("CREX_SERIES", "2gr, 2O6")
    s = Settings.from_env(env_file=None)
    assert (s.scoring_ruleset, s.crex_series) == ("dream11_cricket", ("2GR", "2O6"))


# Full match -------------------------------------------------------------------------------

START = datetime(2026, 10, 24, 14, tzinfo=UTC)
KOHLI, BUMRAH, HEAD = (next(p for p in PLAYERS if p.name.endswith(n)) for n in
                       ("Kohli", "Bumrah", "Head"))  # fmt: skip


@pytest.fixture
async def cricket_repo(tmp_path):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'cricket.db'}")
    await init_db(engine)
    yield Repository(session_factory(engine), CricketStats)
    await engine.dispose()


async def test_full_cricket_match_sends_alerts_and_summary(cricket_repo, crules):
    notifier = FakeNotifier()
    await cricket_repo.upsert_user(7, None)
    for p in (KOHLI, BUMRAH, HEAD):
        await cricket_repo.add_to_squad(7, p, 11)
    await cricket_repo.set_role(7, KOHLI.id, Role.CAPTAIN)
    tracker = LiveTracker(
        MockCricketProvider(START), cricket_repo, crules, notifier,
        clock=lambda: START + timedelta(minutes=5),
    )  # fmt: skip
    await tracker.refresh_schedule()
    for _ in range(12):  # 4 overs per poll, 40 overs; extra polls must be no-ops
        await tracker.poll()

    texts = notifier.texts(7)
    joined = "\n".join(texts)
    assert "Kohli</b> (C) scored 18 runs: <b>+36</b> (×2)" in joined
    assert "Kohli</b> (C) earned the Half-century bonus" in joined
    assert "Bumrah</b> took 1 wicket: <b>+30</b>" in joined
    assert "Head</b> was out for a duck" in joined
    assert "Strike rate" not in joined and "Economy" not in joined
    assert texts[-1].startswith("🏁 <b>Match over</b>")
    # Kohli: (4 XI + 60 runs + 20 fours + 6 six + 8 fifty + 2 SR 150 + 12 run out) x2 = 224
    assert "Kohli</b> (C): <b>224</b> pts" in texts[-1]

    # Snapshots round-trip as CricketStats, so /team totals work after a restart.
    snaps = await cricket_repo.latest_snapshots([KOHLI.id])
    assert snaps[KOHLI.id].stats.runs == 60
    squad = await cricket_repo.get_squad(7)
    assert {m.player.position for m in squad} == {BAT, BOWL}


# Formats ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("T20I", "t20"), ("T20", "t20"), (2, "t20"), ("ODI", "odi"), ("One Day", "odi"),
     ("List A", "odi"), ("Youth ODI", "odi"), (1, "odi"), ("Test", "test"),
     ("First Class", "test"), (3, "test"), ("", ""), (None, "")],
)  # fmt: skip
def test_cricket_format_normalises_source_labels(raw, expected):
    from fantasy_bot.domain import cricket_format

    assert cricket_format(raw) == expected


def test_each_format_scores_with_its_own_rules(crules):
    assert [r.format for r in crules.all_formats] == ["t20", "odi", "test"]
    bowler = CricketStats(in_xi=True, balls_bowled=60, runs_conceded=20, wickets=1)
    t20 = points(bowler, BOWL, crules)
    odi = calculate_points(bowler, BOWL, crules, fmt="odi")
    test = calculate_points(bowler, BOWL, crules, fmt="test")
    assert t20.by_key()["wickets"].points == 30
    assert odi.by_key()["wickets"].points == 25
    assert odi.by_key()["economy"].points == 6  # 2.0 an over: under 2.5 in an ODI
    assert test.by_key()["wickets"].points == 16
    assert "economy" not in test.by_key()  # no rate points in Tests
    assert calculate_points(bowler, BOWL, crules, fmt="").total == t20.total  # unknown -> T20


def test_duck_and_milestones_differ_by_format(crules):
    duck = CricketStats(batted=True, out=True, balls_faced=4)
    assert calculate_points(duck, BAT, crules, fmt="odi").by_key()["duck"].points == -3
    assert calculate_points(duck, BAT, crules, fmt="test").by_key()["duck"].points == -4
    big = CricketStats(batted=True, runs=150, balls_faced=200)
    assert calculate_points(big, BAT, crules, fmt="odi").by_key()["milestone"].points == 24
    assert points(big, BAT, crules).by_key()["milestone"].points == 16  # T20 tops out at 100
