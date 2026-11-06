import pytest

from app.core.errors import RateLimitedError
from app.core.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_hit_blocks_after_limit_and_recovers_after_window():
    clock = FakeClock()
    limiter = RateLimiter(clock)
    for _ in range(3):
        limiter.hit("k", 3, 60)
    with pytest.raises(RateLimitedError):
        limiter.hit("k", 3, 60)

    clock.now += 61
    limiter.hit("k", 3, 60)  # 期間が過ぎたので再び許可される


def test_check_does_not_count_and_keys_are_independent():
    limiter = RateLimiter(FakeClock())
    for _ in range(5):
        limiter.check("a", 1, 60)
    limiter.record("a")
    with pytest.raises(RateLimitedError):
        limiter.check("a", 1, 60)
    limiter.check("b", 1, 60)
