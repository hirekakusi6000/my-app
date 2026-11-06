from datetime import date

import pytest

from app.core.time import calculate_age


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
