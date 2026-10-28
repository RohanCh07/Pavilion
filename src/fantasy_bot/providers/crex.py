"""CREX (crex.com) cricket scraper.

Reads the JSON that CREX embeds in its public, server-rendered pages (see ``crex_parser``):
the home page for the schedule, a match's scorecard tab for live stats and its info tab for
squads. It never calls CREX's private APIs, which robots.txt disallows.

Polite by design: one request at a time with a minimum gap, an honest User-Agent, and
caching (home page 60 s, scorecards 20 s, squads 6 h once the XI is known).
CREX's terms allow personal, non-commercial use; keep this bot to that.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from typing import Any

import httpx

from fantasy_bot.domain import Fixture, FixtureDetails, PlayerInfo, Series
from fantasy_bot.providers import crex_parser as parser
from fantasy_bot.providers.base import ProviderError
from fantasy_bot.utils.cache import MISSING, TTLCache

log = logging.getLogger(__name__)

BASE_URL = "https://crex.com"
HEADERS = {
    "User-Agent": "FantasyPointsBot/0.1 (personal, non-commercial Telegram bot)",
    "Accept": "text/html",
}
MIN_SEARCH_LENGTH = 3
RETRYABLE = frozenset({429, 500, 502, 503, 504})


class CrexProvider:
    def __init__(
        self,
        series: Sequence[str] = (),
        *,
        client: httpx.AsyncClient | None = None,
        retries: int = 2,
        min_interval: float = 1.0,
    ) -> None:
        # Series keys as in CREX URLs (".../series/india-tour-of-new-zealand-2026-2GR" -> 2GR).
        self._series = frozenset(parser.key_to_id(s) for s in series)
        self._retries = retries
        self._min_interval = min_interval
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(20.0, connect=5.0),
            follow_redirects=True,
        )
        self._cache = TTLCache(maxsize=256)
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._schedule: dict[int, Fixture] = {}
        self._warming: asyncio.Task | None = None

    # HTTP --------------------------------------------------------------------------------

    async def _fetch(self, path: str) -> str:
        """GET a page, one request at a time and at most one per ``min_interval``."""
        for attempt in range(self._retries + 1):
            async with self._lock:
                wait = self._last_request + self._min_interval - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                try:
                    resp = await self._client.get(path, headers=HEADERS)
                    retryable = resp.status_code in RETRYABLE
                    resp.raise_for_status()
                    return resp.text
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    error = exc
                    retryable = isinstance(exc, httpx.TransportError) or retryable
                finally:
                    self._last_request = time.monotonic()
            if not retryable or attempt == self._retries:  # a 403/404 won't fix itself
                raise ProviderError(f"CREX {path} failed: {error}") from error
            await asyncio.sleep(2**attempt)
        raise AssertionError("unreachable")

    async def _state(self, path: str, ttl: float) -> dict[str, Any]:
        if (hit := self._cache.get(path, MISSING)) is not MISSING:
            return hit
        try:
            state = parser.extract_state(await self._fetch(path))
        except ValueError as exc:
            raise ProviderError(f"CREX {path}: {exc}") from exc
        self._cache.set(path, state, ttl=ttl)
        return state

    @staticmethod
    def _match_path(fixture_id: int, tab: str) -> str:
        # CREX ignores the slug before "match-updates-<key>", so none is needed.
        return f"/cricket-live-score/match-updates-{parser.id_to_key(fixture_id)}/{tab}"

    # Data --------------------------------------------------------------------------------

    async def _all_fixtures(self) -> list[Fixture]:
        fixtures = parser.map_schedule(await self._state("/", ttl=60))
        if self._series:
            fixtures = [f for f in fixtures if f.league_id in self._series]
        self._schedule.update({f.id: f for f in fixtures})
        return fixtures

    async def _squads(self, fixture_id: int) -> parser.Squads | None:
        key = ("squads", fixture_id)
        if (hit := self._cache.get(key, MISSING)) is not MISSING:
            return hit
        try:
            state = await self._state(self._match_path(fixture_id, "match-details"), ttl=60)
            squads = parser.map_squads(state)
        except ProviderError:
            log.warning("No squads for CREX match %s", parser.id_to_key(fixture_id))
            squads = None
        # XIs don't change once named; squads before the toss can still change.
        self._cache.set(key, squads, ttl=6 * 3600 if squads and squads.playing_xi else 3600)
        return squads

    async def _details(self, fixture_id: int) -> FixtureDetails:
        state = await self._state(self._match_path(fixture_id, "match-scorecard"), ttl=20)
        details = parser.map_scorecard(
            state, parser.id_to_key(fixture_id), await self._squads(fixture_id)
        )
        if known := self._schedule.get(fixture_id):  # the home page's kickoff is exact
            fixture = replace(
                details.fixture,
                kickoff=known.kickoff,
                league_name=known.league_name or details.fixture.league_name,
                format=known.format or details.fixture.format,
            )
            details = FixtureDetails(fixture, details.players)
        return details

    # DataProvider interface --------------------------------------------------------------

    async def _load_all_squads(self) -> list[parser.Squads]:
        # Live first, then upcoming, then finished: the players people are most likely after.
        fixtures = sorted(
            await self._all_fixtures(), key=lambda f: (not f.is_live, f.is_finished, f.kickoff)
        )
        out = []
        for f in fixtures:  # sequential and cached for hours, so only the first pass is slow
            if squads := await self._squads(f.id):
                out.append(squads)
        return out

    def _warm_squads(self) -> None:
        """Load squads in the background so the first /add doesn't wait for ~25 pages."""
        if self._warming is None or self._warming.done():
            self._warming = asyncio.create_task(self._load_all_squads())

    async def search_players(self, query: str) -> list[PlayerInfo]:
        q = query.strip().lower()
        if len(q) < MIN_SEARCH_LENGTH:
            return []
        if self._warming and not self._warming.done():
            await asyncio.shield(self._warming)  # don't fetch the same pages twice
        found: dict[int, PlayerInfo] = {}
        for squads in await self._load_all_squads():
            for p in squads.players:
                if q in p.name.lower():
                    found.setdefault(p.id, p)
        return list(found.values())[:10]

    async def fixtures_on(self, day: date) -> list[Fixture]:
        fixtures = await self._all_fixtures()
        self._warm_squads()
        # Live matches are always included, so multi-day matches stay tracked.
        return [f for f in fixtures if f.kickoff.date() == day or f.is_live]

    async def fixture_details(self, fixture_ids: Sequence[int]) -> list[FixtureDetails]:
        out = []
        for fid in dict.fromkeys(fixture_ids):
            try:
                out.append(await self._details(fid))
            except ProviderError:
                log.exception("CREX scorecard for %s failed", parser.id_to_key(fid))
        if fixture_ids and not out:
            raise ProviderError("CREX: no scorecards could be loaded")
        return out

    async def last_fixture_for_team(self, team_id: int) -> Fixture | None:
        started = [
            f
            for f in await self._all_fixtures()
            if team_id in f.team_ids and (f.is_live or f.is_finished)
        ]
        live = [f for f in started if f.is_live]
        return max(live or started, key=lambda f: f.kickoff, default=None)

    # SeriesProvider interface ------------------------------------------------------------

    async def list_series(self) -> list[Series]:
        series = parser.map_series_list(await self._state("/series", ttl=600))
        if self._series:
            series = [s for s in series if s.id in self._series]
        return series

    async def current_matches(self) -> list[Fixture]:
        return await self._all_fixtures()  # the home page's list, one cached request

    async def series_matches(self, series_id: int) -> list[Fixture]:
        # Like match pages, series pages ignore the slug before the key.
        path = f"/series/s-{parser.id_to_key(series_id)}/matches"
        fixtures = parser.map_series_matches(await self._state(path, ttl=60))
        self._schedule.update({f.id: f for f in fixtures})
        return fixtures

    async def series_players(self, series_id: int) -> list[PlayerInfo]:
        path = f"/series/s-{parser.id_to_key(series_id)}"
        players = parser.map_series_squads(await self._state(path, ttl=6 * 3600))
        if players:
            return players
        # Some series publish no squads; fall back to the squads of their matches.
        found: dict[int, PlayerInfo] = {}
        for f in await self.series_matches(series_id):
            if squads := await self._squads(f.id):
                for p in squads.players:
                    found.setdefault(p.id, p)
        return list(found.values())

    async def aclose(self) -> None:
        if self._warming:
            self._warming.cancel()
        await self._client.aclose()
