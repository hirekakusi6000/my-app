"""エンドポイントで共通に使う Depends。

権限のチェックは次の順に積み重なっている:
  get_current_user          … ログインしているか
  require_password_changed  … 初期パスワードを変更済みか
  require_master / require_general … 権限
"""

import sqlite3

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.rate_limit import RateLimiter
from app.db.connection import get_db
from app.entities.user import Role, User
from app.services.auth_service import AuthService

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


def require_master(user: User = Depends(require_password_changed)) -> User:
    if user.role is not Role.MASTER:
        raise ForbiddenError()
    return user


def require_general(user: User = Depends(require_password_changed)) -> User:
    if user.role is not Role.GENERAL:
        raise ForbiddenError()
    return user
