"""マスターによるユーザー管理。

操作できるのは、マスター自身の組織に所属する一般ユーザーだけ。
他の組織のユーザーは「存在しない」（404）として扱い、存在自体を知られないようにする。
"""

import sqlite3
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email

from app.core import security
from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.time import to_iso, utc_now
from app.entities.user import Role, User, UserSummary
from app.repositories.presence_repository import PresenceRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.avatar_storage import AvatarStorage
from app.services.user_csv import CsvUserRow

MAX_GENERAL_USERS = 50


@dataclass(frozen=True)
class ImportRow:
    line: int
    email: str
    initial_password: str | None
    error: str | None


@dataclass(frozen=True)
class ImportResult:
    rows: list[ImportRow]
    created: bool
    error: str | None  # 行ではなくファイル全体に関するエラー（人数の上限など）


def _normalize_email(value: str) -> tuple[str, str | None]:
    """メールアドレスの形式を確認し、(小文字にそろえた値, エラー) を返す。"""
    if not value:
        return value, "メールアドレスが空欄です"
    try:
        result = validate_email(value, check_deliverability=False)
    except EmailNotValidError:
        return value, "メールアドレスの形式が正しくありません"
    return result.normalized.lower(), None


class UserService:
    def __init__(self, conn: sqlite3.Connection, avatar_storage: AvatarStorage) -> None:
        self.conn = conn
        self.storage = avatar_storage
        self.users = UserRepository(conn)
        self.sessions = SessionRepository(conn)
        self.presence = PresenceRepository(conn)
        self.profiles = ProfileRepository(conn)

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

    def import_users(
        self, master: User, rows: list[CsvUserRow], *, dry_run: bool = False
    ) -> ImportResult:
        """CSV の内容で一般ユーザーをまとめて作成する。

        すべての行を先に確認し、1行でもエラーがあれば1人も作成しない（全件成功か全件取り消し）。
        dry_run=True のときは確認だけ行い、作成しない（初期パスワードの自動生成もしない）。
        """
        org = master.organization_id
        results: list[ImportRow] = []
        seen: set[str] = set()
        for row in rows:
            email, error = _normalize_email(row.email)
            if error is None:
                if email in seen:
                    error = "CSV の中で同じメールアドレスが重複しています"
                elif self.users.email_exists(email):
                    error = "このメールアドレスは既に登録されています"
            password = row.initial_password
            if error is None and password is not None and not (8 <= len(password) <= 128):
                error = "初期パスワードは8〜128文字にしてください"
            seen.add(email)
            results.append(
                ImportRow(line=row.line, email=email, initial_password=password, error=error)
            )

        available = MAX_GENERAL_USERS - self.users.count_by_role(org, Role.GENERAL)
        file_error = None
        if len(rows) > available:
            file_error = (
                f"登録できるユーザーは{MAX_GENERAL_USERS}名までです"
                f"（あと{max(available, 0)}名まで登録できます）"
            )
        valid = file_error is None and all(r.error is None for r in results)
        if not valid or dry_run:
            return ImportResult(rows=results, created=False, error=file_error)

        # 初期パスワードが空欄の人には自動で作る（作った値は結果として一度だけ返す）
        results = [
            ImportRow(
                line=r.line,
                email=r.email,
                initial_password=r.initial_password or security.generate_initial_password(),
                error=None,
            )
            for r in results
        ]
        hashes = [security.hash_password(r.initial_password) for r in results]
        now = to_iso(utc_now())
        try:
            with self.conn:
                for r, password_hash in zip(results, hashes, strict=True):
                    user = self.users.create(
                        organization_id=org,
                        email=r.email,
                        password_hash=password_hash,
                        role=Role.GENERAL,
                        must_change_password=True,
                        now=now,
                    )
                    self.presence.create_initial(user_id=user.id, organization_id=org, now=now)
        except sqlite3.IntegrityError as exc:
            # 確認した後に、同じメールアドレスが別の操作で登録された場合
            raise _email_taken() from exc
        return ImportResult(rows=results, created=True, error=None)

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
        profile = self.profiles.get(target.id, master.organization_id)
        with self.conn:
            self.users.delete(user_id=target.id, organization_id=master.organization_id)
        # DB から消えたことが確定してから、プロフィール画像のファイルを消す
        if profile is not None:
            self.storage.delete(profile.avatar_path)

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
