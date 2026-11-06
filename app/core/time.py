from datetime import UTC, datetime

# DB には常にこの形式（UTC・秒まで・末尾 Z）で保存する。
# 形式が固定なので、文字列のまま大小比較しても日時の前後関係と一致する。
_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime(_ISO_FORMAT)
