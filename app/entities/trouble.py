import sqlite3
from dataclasses import dataclass
from enum import StrEnum


class TroubleStatus(StrEnum):
    OPEN = "open"  # 未解決
    RESOLVED = "resolved"  # 解決済み


@dataclass(frozen=True)
class Trouble:
    id: int
    user_id: int
    author_name: str | None
    author_avatar_path: str | None
    title: str
    body: str
    status: TroubleStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Trouble":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            author_name=row["author_name"],
            author_avatar_path=row["author_avatar_path"],
            title=row["title"],
            body=row["body"],
            status=TroubleStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
