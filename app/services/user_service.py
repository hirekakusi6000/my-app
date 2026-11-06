"""マスターによるユーザー管理。

操作できるのは、マスター自身の組織に所属する一般ユーザーだけ。
他の組織のユーザーは「存在しない」（404）として扱い、存在自体を知られないようにする。
"""

import sqlite3

from app.core import security
from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.time import to_iso, utc_now
from app.entities.user import Role, User, UserSummary
from app.repositories.presence_repository import PresenceRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

MAX_GENERAL_USERS = 50


class UserService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.users = UserRepository(conn)
        self.sessions = SessionRepository(conn)
        self.presence = PresenceRepository(conn)

    def list_users(self, master: User) -> list[UserSummary]:
        return self.users.list_summaries(master.organization_id)

    def create_general_user(self, master: User, *, email: str, initial_password: str) -> User:
        password_hash = security.hash_password(initial_password)
        now = to_iso(utc_now())
        try:
            with self.conn:
                count = self.users.count_by_role(master.organization_id, Role.GENERAL)
                if count >= MAX_GENERAL_USERS:
                    raise BusinessRuleError(
                        f"登録できるユーザーは{MAX_GENERAL_USERS}名までです", code="LIMIT_EXCEEDED"
                    )
                if self.users.email_exists(email):
                    raise _email_taken()
                user = self.users.create(
                    organization_id=master.organization_id,
                    email=email,
                    password_hash=password_hash,
                    role=Role.GENERAL,
                    must_change_password=True,
                    now=now,
                )
                self.presence.create_initial(
                    user_id=user.id, organization_id=master.organization_id, now=now
                )
        except sqlite3.IntegrityError as exc:
            raise _email_taken() from exc
        return user

    def update_email(self, master: User, user_id: int, *, email: str) -> User:
        target = self._get_general_user(master, user_id)
        try:
            with self.conn:
                if self.users.email_exists(email, exclude_user_id=target.id):
                    raise _email_taken()
                self.users.update_email(
                    user_id=target.id,
                    organization_id=master.organization_id,
                    email=email,
                    now=to_iso(utc_now()),
                )
        except sqlite3.IntegrityError as exc:
            raise _email_taken() from exc
        updated = self.users.get(target.id, master.organization_id)
        assert updated is not None
        return updated

    def reset_password(self, master: User, user_id: int, *, new_password: str) -> None:
        """パスワードを再設定し、次のログインで本人に変更させる。"""
        target = self._get_general_user(master, user_id)
        with self.conn:
            self.users.update_password(
                user_id=target.id,
                organization_id=master.organization_id,
                password_hash=security.hash_password(new_password),
                must_change_password=True,
                now=to_iso(utc_now()),
            )
            # 古いパスワードでログイン中の端末もログアウトさせる
            self.sessions.delete_all_for_user(target.id)

    def delete_user(self, master: User, user_id: int) -> None:
        """物理削除。座っていた座席は、在席状態の行が一緒に消えることで空く。"""
        target = self._get_general_user(master, user_id)
        with self.conn:
            self.users.delete(user_id=target.id, organization_id=master.organization_id)

    def _get_general_user(self, master: User, user_id: int) -> User:
        if user_id == master.id:
            raise BusinessRuleError(
                "自分自身はこの画面から操作できません", code="CANNOT_MODIFY_SELF"
            )
        target = self.users.get(user_id, master.organization_id)
        if target is None or target.role is not Role.GENERAL:
            raise NotFoundError("ユーザーが見つかりません")
        return target


def _email_taken() -> ConflictError:
    return ConflictError("このメールアドレスは既に登録されています", code="EMAIL_TAKEN")
