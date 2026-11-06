"""エンドポイントで共通に使う Depends。

権限のチェックは次の順に積み重なっている:
  get_current_user          … ログインしているか
  require_password_changed  … 初期パスワードを変更済みか
  require_active_user       … 一般ユーザーならプロフィールも登録済みか
  require_master / require_general … 権限
"""

import sqlite3

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.rate_limit import RateLimiter
from app.db.connection import get_db
from app.entities.user import Role, User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.avatar_storage import AvatarStorage

SESSION_COOKIE = "session"


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def get_auth_service(
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings_from_app),
) -> AuthService:
    return AuthService(conn, session_expire_hours=settings.session_expire_hours)


def get_session_token(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise UnauthenticatedError()
    return token


def get_current_user(
    token: str = Depends(get_session_token),
    service: AuthService = Depends(get_auth_service),
) -> User:
    user = service.authenticate(token)
    if user is None:
        raise UnauthenticatedError("ログインの有効期限が切れました。もう一度ログインしてください")
    return user


def require_password_changed(user: User = Depends(get_current_user)) -> User:
    if user.must_change_password:
        raise ForbiddenError("パスワードを変更してください", code="PASSWORD_CHANGE_REQUIRED")
    return user


def require_active_user(
    user: User = Depends(require_password_changed),
    conn: sqlite3.Connection = Depends(get_db),
) -> User:
    """初回設定（パスワード変更・プロフィール登録）が終わったユーザー。マスターはそのまま通す。"""
    if user.role is Role.GENERAL and not UserRepository(conn).has_profile(user.id):
        raise ForbiddenError("プロフィールを登録してください", code="SETUP_REQUIRED")
    return user


def get_avatar_storage(settings: Settings = Depends(get_settings_from_app)) -> AvatarStorage:
    return AvatarStorage(settings.upload_dir)


def require_master(user: User = Depends(require_password_changed)) -> User:
    if user.role is not Role.MASTER:
        raise ForbiddenError()
    return user


def require_general(user: User = Depends(require_password_changed)) -> User:
    if user.role is not Role.GENERAL:
        raise ForbiddenError()
    return user
