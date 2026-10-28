from fantasy_bot.domain import PlayerInfo, PlayerStats, Position, Role
from fantasy_bot.storage import AddResult

SAKA = PlayerInfo(1, "Bukayo Saka", 42, "Arsenal", Position.FORWARD)
RAYA = PlayerInfo(2, "David Raya", 42, "Arsenal", Position.GOALKEEPER)
PALMER = PlayerInfo(3, "Cole Palmer", 49, "Chelsea", Position.MIDFIELDER)


async def test_add_respects_size_and_duplicates(repo):
    await repo.upsert_user(10, "rohan")
    assert await repo.add_to_squad(10, SAKA, max_size=2) is AddResult.ADDED
    assert await repo.add_to_squad(10, SAKA, max_size=2) is AddResult.ALREADY_IN_SQUAD
    assert await repo.add_to_squad(10, RAYA, max_size=2) is AddResult.ADDED
    assert await repo.add_to_squad(10, PALMER, max_size=2) is AddResult.SQUAD_FULL
    assert [m.player for m in await repo.get_squad(10)] == [SAKA, RAYA]


async def test_captain_is_unique(repo):
    await repo.upsert_user(10, None)
    for p in (SAKA, RAYA):
        await repo.add_to_squad(10, p, 11)
    await repo.set_role(10, SAKA.id, Role.CAPTAIN)
    await repo.set_role(10, RAYA.id, Role.CAPTAIN)
    roles = {m.player.id: m.role for m in await repo.get_squad(10)}
    assert roles == {SAKA.id: Role.PLAYER, RAYA.id: Role.CAPTAIN}


async def test_subscribers_skip_users_with_alerts_off(repo):
    for chat in (10, 20):
        await repo.upsert_user(chat, None)
        await repo.add_to_squad(chat, SAKA, 11)
    await repo.set_alerts(20, False)
    subs = await repo.subscribers([SAKA.id])
    assert list(subs) == [10]
    assert await repo.tracked_team_ids() == {42}


async def test_snapshots_roundtrip_and_latest(repo):
    await repo.save_snapshots(500, "A 1-0 B", {SAKA.id: PlayerStats(minutes=90, goals=1)})
    await repo.save_snapshots(501, "C 0-0 D", {SAKA.id: PlayerStats(minutes=45)})
    assert (await repo.get_snapshots(500, [SAKA.id]))[SAKA.id].goals == 1
    latest = (await repo.latest_snapshots([SAKA.id]))[SAKA.id]
    assert (latest.fixture_id, latest.fixture_label) == (501, "C 0-0 D")


async def test_remove(repo):
    await repo.upsert_user(10, None)
    await repo.add_to_squad(10, SAKA, 11)
    assert await repo.remove_from_squad(10, SAKA.id)
    assert not await repo.remove_from_squad(10, SAKA.id)
    assert await repo.get_squad(10) == []


async def test_init_db_adds_pool_column_to_an_old_database(tmp_path):
    from sqlalchemy import text

    from fantasy_bot.storage import create_engine, init_db

    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    async with engine.begin() as conn:  # the fantasy_teams table as it first shipped
        await conn.execute(
            text("CREATE TABLE fantasy_teams (id INTEGER PRIMARY KEY, owner VARCHAR(64))")
        )
    await init_db(engine)
    async with engine.begin() as conn:
        cols = [r[1] for r in await conn.execute(text("PRAGMA table_info(fantasy_teams)"))]
    assert "pool_id" in cols
    await engine.dispose()
