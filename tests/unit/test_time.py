from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.time import JST, calculate_age, is_before_today_jst, start_of_today_jst, to_iso


def test_start_of_today_jst_is_midnight_in_japan():
    start = datetime.strptime(start_of_today_jst(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    in_japan = start.astimezone(JST)
    assert (in_japan.hour, in_japan.minute, in_japan.second) == (0, 0, 0)
    assert in_japan.date() == datetime.now(JST).date()


def test_is_before_today_jst():
    start = datetime.strptime(start_of_today_jst(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert is_before_today_jst(to_iso(start - timedelta(seconds=1))) is True  # 昨日の23:59:59
    assert is_before_today_jst(to_iso(start)) is False  # 今日の0時ちょうど
    assert is_before_today_jst(to_iso(datetime.now(UTC))) is False


@pytest.mark.parametrize(
    ("birth", "today", "expected"),
    [
        (date(1990, 4, 1), date(2026, 3, 31), 35),  # 誕生日の前日
        (date(1990, 4, 1), date(2026, 4, 1), 36),  # 誕生日当日
        (date(2000, 2, 29), date(2026, 2, 28), 25),  # うるう日生まれ・平年
        (date(2000, 2, 29), date(2026, 3, 1), 26),
        (date(2000, 2, 29), date(2028, 2, 29), 28),  # うるう年の当日
        (date(2026, 11, 6), date(2026, 11, 6), 0),
    ],
)
def test_calculate_age(birth, today, expected):
    assert calculate_age(birth, today) == expected
