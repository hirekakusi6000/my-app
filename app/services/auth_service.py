import sqlite3
from dataclasses import dataclass
from datetime import timedelta

from app.core import security
from app.core.errors import BusinessRuleError, ConflictError, UnauthenticatedError
from app.core.time import to_iso, utc_now
from app.entities.user import Organization, Role, User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.master_data_service import MasterDataService


@dataclass(frozen=True)
class AuthResult:
    user: User
    token: str


@dataclass(frozen=True)
class Account:
    """GET /me で返す、ログイン中ユーザーの情報。"""

    user: User
    organization: Organization
    profile_completed: bool


class AuthService:
    def __init__(self, conn: sqlite3.Connection, *, session_expire_hours: int) -> None:
        self.conn = conn
        self.session_expire = timedelta(hours=session_expire_hours)
        self.organizations = OrganizationRepository(conn)
        self.users = UserRepository(conn)
        self.sessions = SessionRepository(conn)

    # ───────── 新規登録・ログイン・ログアウト ─────────

    def signup(self, *, organization_name: str, email: str, password: str) -> AuthResult:
        """組織とマスターを作成し、そのままログインした状態にする。"""
        password_hash = security.hash_password(password)
        now = to_iso(utc_now())
        try:
            with self.conn:
                if self.users.email_exists(email):
                    raise _email_taken()
                org = self.organizations.create(organization_name, now)
                user = self.users.create(
                    organization_id=org.id,
                    email=email,
                    password_hash=password_hash,
                    role=Role.MASTER,
                    must_change_password=False,
                    now=now,
                )
                MasterDataService(self.conn).seed_defaults(org.id)
                token = self._create_session(user.id)
        except sqlite3.IntegrityError as exc:
            # 同時に同じメールアドレスで登録された場合
            raise _email_taken() from exc
        return AuthResult(user=user, token=token)

    def login(self, *, email: str, password: str) -> AuthResult:
        user = self.users.get_by_email(email)
        if user is None:
            security.verify_dummy_password(password)
            raise _invalid_credentials()
        if not security.verify_password(password, user.password_hash):
            raise _invalid_credentials()
        with self.conn:
            self.sessions.delete_expired(to_iso(utc_now()))
            token = self._create_session(user.id)
        return AuthResult(user=user, token=token)

    def logout(self, token: str) -> None:
        with self.conn:
            self.sessions.delete(security.hash_session_token(token))

    def authenticate(self, token: str) -> User | None:
        return self.sessions.find_user(security.hash_session_token(token), to_iso(utc_now()))

    # ───────── 自分の情報・パスワード変更 ─────────

    def get_account(self, user: User) -> Account:
        organization = self.organizations.get(user.organization_id)
        assert organization is not None  # users.organization_id は外部キーで保証されている
        return Account(
            user=user,
            organization=organization,
            profile_completed=self.users.has_profile(user.id),
        )

    def change_password(
        self, user: User, *, current_token: str, current_password: str, new_password: str
    ) -> None:
        if not security.verify_password(current_password, user.password_hash):
            raise BusinessRuleError("現在のパスワードが違います", code="INVALID_CURRENT_PASSWORD")
        if security.verify_password(new_password, user.password_hash):
            raise BusinessRuleError(
                "新しいパスワードは現在のパスワードと別のものにしてください", code="SAME_PASSWORD"
            )
        with self.conn:
            self.users.update_password(
                user_id=user.id,
                organization_id=user.organization_id,
                password_hash=security.hash_password(new_password),
                must_change_password=False,
                now=to_iso(utc_now()),
            )
            # 他の端末のログインは無効にする（今使っているセッションだけ残す）
            self.sessions.delete_others(
                user_id=user.id, keep_token_hash=security.hash_session_token(current_token)
            )

    # ───────── 内部処理 ─────────

    def _create_session(self, user_id: int) -> str:
        """セッションを作成する。呼び出し側のトランザクションの中で使う。"""
        token = security.generate_session_token()
        now = utc_now()
        self.sessions.create(
            token_hash=security.hash_session_token(token),
            user_id=user_id,
            expires_at=to_iso(now + self.session_expire),
            now=to_iso(now),
        )
        return token


def _email_taken() -> ConflictError:
    return ConflictError("このメールアドレスは既に登録されています", code="EMAIL_TAKEN")


def _invalid_credentials() -> UnauthenticatedError:
    return UnauthenticatedError(
        "メールアドレスまたはパスワードが違います", code="INVALID_CREDENTIALS"
    )
