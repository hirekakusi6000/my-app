from datetime import UTC, date, datetime, timedelta, timezone

# DB には常にこの形式（UTC・秒まで・末尾 Z）で保存する。
# 形式が固定なので、文字列のまま大小比較しても日時の前後関係と一致する。
_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# 日本時間（夏時間がないので固定の +9 時間でよい）。
# zoneinfo は Windows ではタイムゾーンのデータが別途必要になるため使わない。
JST = timezone(timedelta(hours=9), "JST")


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime(_ISO_FORMAT)


def today_jst() -> date:
    return datetime.now(JST).date()


def calculate_age(birth_date: date, today: date) -> int:
    """満年齢。誕生日の前日までは1つ少ない（2月29日生まれは平年の3月1日に加算）。"""
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)
