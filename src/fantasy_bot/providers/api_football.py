"""API-Football v3 client (https://www.api-football.com/documentation-v3).

Quota-aware by design: the free plan allows 100 requests/day, so
- the day's fixture list is one request (``/fixtures?date=``) filtered locally by league,
- live detail for up to 20 fixtures is one request (``/fixtures?ids=``) that embeds score,
  events and per-player stats,
- read-mostly calls (search, last fixture) go through a short TTL cache.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import date
from typing import Any

import httpx

from fantasy_bot.domain import Fixture, FixtureDetails, PlayerInfo
from fantasy_bot.providers import api_football_mapper as mapper
from fantasy_bot.providers.base import ProviderError
from fantasy_bot.utils.cache import MISSING, TTLCache

log = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
MAX_IDS_PER_CALL = 20
MIN_SEARCH_LENGTH = 4  # API-Football rejects shorter player searches


class ApiFootballProvider:
    def __init__(
        self,
        api_key: str,
        league_ids: Sequence[int],
        season: int,
        *,
        client: httpx.AsyncClient | None = None,
        retries: int = 2,
    ) -> None:
        self._league_ids = frozenset(league_ids)
        self._season = season
        self._retries = retries
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"x-apisports-key": api_key},
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        self._cache = TTLCache(maxsize=512)

    async def _get(self, path: str, **params: Any) -> list[dict[str, Any]]:
        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.get(path, params=params)
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
                resp.raise_for_status()
                body = resp.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt == self._retries:
                    raise ProviderError(f"API-Football {path} failed: {exc}") from exc
                await asyncio.sleep(2**attempt)
                continue

            # API-Football reports quota/auth problems as HTTP 200 with an "errors" field.
            if errors := body.get("errors"):
                raise ProviderError(f"API-Football {path} error: {errors}")
            remaining = resp.headers.get("x-ratelimit-requests-remaining")
            log.debug(
                "GET %s %s -> %d items (quota left: %s)",
                path,
                params,
                body.get("results", 0),
                remaining,
            )
            return body.get("response") or []
        raise AssertionError("unreachable")

    async def search_players(self, query: str) -> list[PlayerInfo]:
        query = query.strip()
        if len(query) < MIN_SEARCH_LENGTH:
            return []
        key = ("search", query.lower())
        if (hit := self._cache.get(key, MISSING)) is not MISSING:
            return hit

        # /players needs a league or team alongside search, so ask each followed league.
        batches = await asyncio.gather(
            *(
                self._get("/players", search=query, league=lg, season=self._season)
                for lg in sorted(self._league_ids)
            )
        )
        seen: dict[int, PlayerInfo] = {}
        for item in (i for batch in batches for i in batch):
            if (info := mapper.map_player_search(item)) and info.id not in seen:
                seen[info.id] = info
        result = list(seen.values())[:10]
        self._cache.set(key, result, ttl=3600)
        return result

    async def fixtures_on(self, day: date) -> list[Fixture]:
        key = ("day", day.isoformat())
        if (hit := self._cache.get(key, MISSING)) is not MISSING:
            return hit
        items = await self._get("/fixtures", date=day.isoformat(), timezone="UTC")
        result = [mapper.map_fixture(i) for i in items if i["league"]["id"] in self._league_ids]
        self._cache.set(key, result, ttl=300)
        return result

    async def fixture_details(self, fixture_ids: Sequence[int]) -> list[FixtureDetails]:
        ids = list(dict.fromkeys(fixture_ids))
        chunks = [ids[i : i + MAX_IDS_PER_CALL] for i in range(0, len(ids), MAX_IDS_PER_CALL)]
        batches = await asyncio.gather(
            *(self._get("/fixtures", ids="-".join(map(str, c))) for c in chunks)
        )
        return [mapper.map_fixture_details(i) for batch in batches for i in batch]

    async def last_fixture_for_team(self, team_id: int) -> Fixture | None:
        key = ("last", team_id)
        if (hit := self._cache.get(key, MISSING)) is not MISSING:
            return hit
        live = await self._get("/fixtures", team=team_id, live="all")
        items = live or await self._get("/fixtures", team=team_id, last=1)
        result = mapper.map_fixture(items[0]) if items else None
        self._cache.set(key, result, ttl=120)
        return result

    async def aclose(self) -> None:
        await self._client.aclose()
