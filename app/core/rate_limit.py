"""メモリ上で回数を数える、シンプルな試行回数の制限（スライディングウィンドウ方式）。

Uvicorn を1プロセスで動かす前提。複数プロセスにする場合は、DB などの共有の保存先が必要になる。
"""

import threading
import time
from collections import deque
from collections.abc import Callable

from app.core.errors import RateLimitedError


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, window_seconds: float) -> deque[float]:
        now = self._clock()
        hits = self._hits.get(key)
        if hits is None:
            return deque()
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if not hits:
            del self._hits[key]
        return hits

    def check(self, key: str, limit: int, window_seconds: float) -> None:
        """制限を超えていれば RateLimitedError を投げる（回数は数えない）。"""
        with self._lock:
            if len(self._recent(key, window_seconds)) >= limit:
                raise RateLimitedError()

    def record(self, key: str) -> None:
        with self._lock:
            self._hits.setdefault(key, deque()).append(self._clock())

    def hit(self, key: str, limit: int, window_seconds: float) -> None:
        """制限を確認してから1回数える。"""
        with self._lock:
            if len(self._recent(key, window_seconds)) >= limit:
                raise RateLimitedError()
            self._hits.setdefault(key, deque()).append(self._clock())
