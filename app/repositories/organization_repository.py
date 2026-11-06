import sqlite3

from app.entities.user import Organization


class OrganizationRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, name: str, now: str) -> Organization:
        cur = self.conn.execute(
            "INSERT INTO organizations (name, created_at) VALUES (?, ?)", (name, now)
        )
        return Organization(id=cur.lastrowid, name=name, created_at=now)

    def get(self, organization_id: int) -> Organization | None:
        row = self.conn.execute(
            "SELECT id, name, created_at FROM organizations WHERE id = ?", (organization_id,)
        ).fetchone()
        return Organization.from_row(row) if row else None
