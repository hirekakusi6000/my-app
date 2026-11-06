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

    def rename(self, organization_id: int, name: str) -> None:
        self.conn.execute("UPDATE organizations SET name = ? WHERE id = ?", (name, organization_id))

    def avatar_paths(self, organization_id: int) -> list[str]:
        """組織の従業員のプロフィール画像のファイル名（組織の削除時にファイルも消すため）。"""
        rows = self.conn.execute(
            "SELECT p.avatar_path FROM profiles p JOIN users u ON u.id = p.user_id"
            " WHERE u.organization_id = ? AND p.avatar_path IS NOT NULL",
            (organization_id,),
        ).fetchall()
        return [r["avatar_path"] for r in rows]

    def delete(self, organization_id: int) -> None:
        """組織を削除する。

        ユーザー・セッション・プロフィール・スキル・在席状態・候補の一覧・フロア・部屋・家具は、
        外部キーの ON DELETE CASCADE で一緒に削除される。
        在席状態の座席（NO ACTION）が家具より後に残らないよう、先に在席状態を消しておく。
        """
        self.conn.execute("DELETE FROM presence WHERE organization_id = ?", (organization_id,))
        self.conn.execute("DELETE FROM organizations WHERE id = ?", (organization_id,))
