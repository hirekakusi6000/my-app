from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import (
    SESSION_COOKIE,
    get_auth_service,
    get_rate_limiter,
    get_settings_from_app,
)
from app.api.v1.presenters import to_me_response
from app.core.config import Settings
from app.core.errors import UnauthenticatedError
from app.core.rate_limit import RateLimiter
from app.schemas.auth import LoginRequest, MeResponse, SignupRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

SIGNUP_LIMIT = (5, 60 * 60)  # 同じ IP から 1時間に5回まで
LOGIN_FAILURE_LIMIT = (10, 5 * 60)  # 同じ IP＋メールで 5分に10回まで（失敗した回数）


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_expire_hours * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/signup", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings_from_app),
) -> MeResponse:
    limiter.hit(f"signup:{_client_ip(request)}", *SIGNUP_LIMIT)
    result = service.signup(
        organization_name=body.organization_name, email=body.email, password=body.password
    )
    _set_session_cookie(response, result.token, settings)
    return to_me_response(service.get_account(result.user))


@router.post("/login", response_model=MeResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings_from_app),
) -> MeResponse:
    key = f"login:{_client_ip(request)}:{body.email}"
    limit, window = LOGIN_FAILURE_LIMIT
    limiter.check(key, limit, window)
    try:
        result = service.login(email=body.email, password=body.password)
    except UnauthenticatedError:
        limiter.record(key)
        raise
    _set_session_cookie(response, result.token, settings)
    return to_me_response(service.get_account(result.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        service.logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/")
