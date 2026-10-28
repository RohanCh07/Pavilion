"""End-to-end: scripted mock match -> tracker -> alerts, against a real SQLite database."""

from datetime import UTC, datetime, timedelta

from conftest import FakeNotifier
from fantasy_bot.domain import Role
from fantasy_bot.live.tracker import LiveTracker
from fantasy_bot.providers.mock import PLAYERS, MockProvider

KICKOFF = datetime(2026, 10, 21, 19, tzinfo=UTC)
SAKA, RAYA, PALMER = (
    next(p for p in PLAYERS if p.name.endswith(n)) for n in ("Saka", "Raya", "Palmer")
)


def clock():
    return KICKOFF + timedelta(minutes=5)


async def _setup(repo, chat=10, players=(SAKA, RAYA), captain=SAKA):
    await repo.upsert_user(chat, None)
    for p in players:
        await repo.add_to_squad(chat, p, 11)
    if captain:
        await repo.set_role(chat, captain.id, Role.CAPTAIN)


async def _play_match(tracker):
    await tracker.refresh_schedule()
    for _ in range(10):  # 15 simulated minutes per poll; extra polls must be no-ops
        await tracker.poll()


async def test_full_match_sends_alerts_and_summary(repo, rules, notifier):
    await _setup(repo)
    tracker = LiveTracker(MockProvider(KICKOFF), repo, rules, notifier, clock=clock)
    await _play_match(tracker)

    texts = notifier.texts(10)
    joined = "\n".join(texts)
    assert "Saka</b> (C) scored: <b>+12</b> (×2)" in joined  # Saka's goal, doubled as captain
    assert "saved a penalty" in joined  # Raya's penalty save
    assert texts[-1].startswith("🏁 <b>Full time</b>")
    # Saka (C): (4 start + 6 goal + 8 assist) x2 = 36
    assert "Saka</b> (C): <b>36</b> pts" in texts[-1]


async def test_no_api_calls_when_nobody_tracks_the_teams(repo, rules, notifier):
    provider = MockProvider(KICKOFF)
    tracker = LiveTracker(provider, repo, rules, notifier, clock=clock)
    await _play_match(tracker)
    assert provider.minute == 0 and notifier.sent == []


async def test_restart_does_not_repeat_alerts(repo, rules, notifier):
    await _setup(repo)
    provider = MockProvider(KICKOFF)
    first = LiveTracker(provider, repo, rules, notifier, clock=clock)
    await first.refresh_schedule()
    await first.poll()
    await first.poll()  # minute 30: Saka has scored
    before = len(notifier.sent)

    provider.minute -= 15  # the restarted bot sees the same minute-30 data again
    restarted = LiveTracker(provider, repo, rules, notifier, clock=clock)
    await restarted.refresh_schedule()
    await restarted.poll()
    assert len(notifier.sent) == before


async def test_alerts_only_go_to_owners(repo, rules, notifier):
    await _setup(repo, chat=10, players=(SAKA,), captain=None)
    await _setup(repo, chat=20, players=(PALMER,), captain=None)
    tracker = LiveTracker(MockProvider(KICKOFF), repo, rules, notifier, clock=clock)
    await _play_match(tracker)
    assert all("Palmer" not in t for t in notifier.texts(10))
    assert all("Saka" not in t for t in notifier.texts(20))
    assert any("missed a penalty" in t for t in notifier.texts(20))


async def test_unreachable_user_gets_alerts_disabled(repo, rules):
    notifier = FakeNotifier(unreachable={10})
    await _setup(repo)
    tracker = LiveTracker(MockProvider(KICKOFF), repo, rules, notifier, clock=clock)
    await _play_match(tracker)
    assert await repo.subscribers([SAKA.id]) == {}
