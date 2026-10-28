from __future__ import annotations

import pytest

from fantasy_bot.scoring import load_rules
from fantasy_bot.storage import Repository, create_engine, init_db, session_factory


@pytest.fixture
def rules():
    return load_rules("dream11_football")


@pytest.fixture
async def repo(tmp_path):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await init_db(engine)
    yield Repository(session_factory(engine))
    await engine.dispose()


class FakeNotifier:
    def __init__(self, unreachable: set[int] | None = None) -> None:
        self.sent: list[tuple[int, str]] = []
        self.unreachable = unreachable or set()

    async def send(self, chat_id: int, html: str) -> bool:
        if chat_id in self.unreachable:
            return False
        self.sent.append((chat_id, html))
        return True

    def texts(self, chat_id: int) -> list[str]:
        return [t for c, t in self.sent if c == chat_id]


@pytest.fixture
def notifier():
    return FakeNotifier()
