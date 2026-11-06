import sqlite3

from app.entities.trouble import Trouble, TroubleStatus

_SELECT = (
    "SELECT t.id, t.user_id, t.title, t.body, t.status, t.created_at, t.updated_at,"
    "       p.name AS author_name, p.avatar_path AS author_avatar_path"
    " FROM troubles t LEFT JOIN profiles p ON p.user_id = t.user_id"
)


class TroubleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(
        self,
        organization_id: int,
        *,
        status: TroubleStatus | None = None,
        user_id: int | None = None,
    ) -> list[Trouble]:
        rows = self.conn.execute(
            f"{_SELECT}"
            " WHERE t.organization_id = ?"
            "   AND (? IS NULL OR t.status = ?)"
            "   AND (? IS NULL OR t.user_id = ?)"
            " ORDER BY t.updated_at DESC, t.id DESC",
            (organization_id, status, status, user_id, user_id),
        ).fetchall()
        return [Trouble.from_row(r) for r in rows]

    def get(self, trouble_id: int, organization_id: int) -> Trouble | None:
        row = self.conn.execute(
            f"{_SELECT} WHERE t.id = ? AND t.organization_id = ?",
            (trouble_id, organization_id),
        ).fetchone()
        return Trouble.from_row(row) if row else None

    def create(self, *, organization_id: int, user_id: int, title: str, body: str, now: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO troubles (organization_id, user_id, title, body, status,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, 'open', ?, ?)",
            (organization_id, user_id, title, body, now, now),
        )
        return cur.lastrowid

    def update(
        self,
        *,
        trouble_id: int,
        organization_id: int,
        title: str,
        body: str,
        status: TroubleStatus,
        now: str,
    ) -> None:
        self.conn.execute(
            "UPDATE troubles SET title = ?, body = ?, status = ?, updated_at = ?"
            " WHERE id = ? AND organization_id = ?",
            (title, body, status.value, now, trouble_id, organization_id),
        )

    def delete(self, trouble_id: int, organization_id: int) -> None:
        self.conn.execute(
            "DELETE FROM troubles WHERE id = ? AND organization_id = ?",
            (trouble_id, organization_id),
        )

    def users_with_open_troubles(self, organization_id: int) -> set[int]:
        rows = self.conn.execute(
            "SELECT DISTINCT user_id FROM troubles WHERE organization_id = ? AND status = 'open'",
            (organization_id,),
        ).fetchall()
        return {r["user_id"] for r in rows}
