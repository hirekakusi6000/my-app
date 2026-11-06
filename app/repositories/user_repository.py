import sqlite3

from app.entities.user import Role, User, UserSummary

_COLUMNS = (
    "id, organization_id, email, password_hash, role, must_change_password, created_at, updated_at"
)


class UserRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(
        self,
        *,
        organization_id: int,
        email: str,
        password_hash: str,
        role: Role,
        must_change_password: bool,
        now: str,
    ) -> User:
        cur = self.conn.execute(
            "INSERT INTO users"
            " (organization_id, email, password_hash, role, must_change_password,"
            "  created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                organization_id,
                email,
                password_hash,
                role.value,
                int(must_change_password),
                now,
                now,
            ),
        )
        return User(
            id=cur.lastrowid,
            organization_id=organization_id,
            email=email,
            password_hash=password_hash,
            role=role,
            must_change_password=must_change_password,
            created_at=now,
            updated_at=now,
        )

    def get(self, user_id: int, organization_id: int) -> User | None:
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM users WHERE id = ? AND organization_id = ?",
            (user_id, organization_id),
        ).fetchone()
        return User.from_row(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        """ログイン用。メールアドレスはシステム全体で一意なので、組織では絞り込まない。"""
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM users WHERE email = ?", (email,)
        ).fetchone()
        return User.from_row(row) if row else None

    def email_exists(self, email: str, *, exclude_user_id: int | None = None) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM users WHERE email = ? AND id IS NOT ?", (email, exclude_user_id)
        ).fetchone()
        return row is not None

    def list_summaries(self, organization_id: int) -> list[UserSummary]:
        """ユーザー管理画面の一覧用。プロフィールの名前も一緒に取得する。"""
        rows = self.conn.execute(
            "SELECT u.id, u.email, u.role, u.must_change_password, u.created_at,"
            "       p.name AS profile_name"
            " FROM users u LEFT JOIN profiles p ON p.user_id = u.id"
            " WHERE u.organization_id = ?"
            " ORDER BY u.role = 'general', u.created_at, u.id",
            (organization_id,),
        ).fetchall()
        return [UserSummary.from_row(row) for row in rows]

    def count_by_role(self, organization_id: int, role: Role) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE organization_id = ? AND role = ?",
            (organization_id, role.value),
        ).fetchone()[0]

    def update_email(self, *, user_id: int, organization_id: int, email: str, now: str) -> None:
        self.conn.execute(
            "UPDATE users SET email = ?, updated_at = ? WHERE id = ? AND organization_id = ?",
            (email, now, user_id, organization_id),
        )

    def delete(self, *, user_id: int, organization_id: int) -> None:
        """物理削除。関連するデータは外部キーの ON DELETE CASCADE で一緒に削除される。"""
        self.conn.execute(
            "DELETE FROM users WHERE id = ? AND organization_id = ?", (user_id, organization_id)
        )

    def update_password(
        self,
        *,
        user_id: int,
        organization_id: int,
        password_hash: str,
        must_change_password: bool,
        now: str,
    ) -> None:
        self.conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = ?, updated_at = ?"
            " WHERE id = ? AND organization_id = ?",
            (password_hash, int(must_change_password), now, user_id, organization_id),
        )

    def has_profile(self, user_id: int) -> bool:
        row = self.conn.execute("SELECT 1 FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None
