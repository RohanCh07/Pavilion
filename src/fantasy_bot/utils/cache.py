"""A tiny TTL cache; enough for API responses without pulling in another dependency."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Hashable
from typing import Any

MISSING = object()


class TTLCache:
    def __init__(self, maxsize: int = 256, clock=time.monotonic) -> None:
        self._data: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._clock = clock

    def get(self, key: Hashable, default: Any = None) -> Any:
        entry = self._data.get(key, MISSING)
        if entry is MISSING:
            return default
        expires, value = entry
        if expires < self._clock():
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def set(self, key: Hashable, value: Any, ttl: float) -> None:
        self._data[key] = (self._clock() + ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
