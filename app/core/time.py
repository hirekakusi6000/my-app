from datetime import UTC, date, datetime, time, timedelta, timezone

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


def start_of_today_jst() -> str:
    """日本時間の今日の0時を、DB と同じ形式（UTC の ISO 文字列）で返す。"""
    return to_iso(datetime.combine(today_jst(), time(0, 0), tzinfo=JST))


def is_before_today_jst(iso: str) -> bool:
    """DB の日時（UTC の ISO 文字列）が、日本時間の今日より前か。"""
    return iso < start_of_today_jst()


def calculate_age(birth_date: date, today: date) -> int:
    """満年齢。誕生日の前日までは1つ少ない（2月29日生まれは平年の3月1日に加算）。"""
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)
