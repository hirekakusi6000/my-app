import sqlite3
from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    MASTER = "master"
    GENERAL = "general"


@dataclass(frozen=True)
class Organization:
    id: int
    name: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Organization":
        return cls(id=row["id"], name=row["name"], created_at=row["created_at"])


@dataclass(frozen=True)
class User:
    id: int
    organization_id: int
    email: str
    password_hash: str
    role: Role
    must_change_password: bool
    created_at: str
    updated_at: str

    @property
    def is_master(self) -> bool:
        return self.role is Role.MASTER

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        return cls(
            id=row["id"],
            organization_id=row["organization_id"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=Role(row["role"]),
            must_change_password=bool(row["must_change_password"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
