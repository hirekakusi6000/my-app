"""業務エラーの定義と、HTTP レスポンスへの変換。

service 層は HTTP を知らずに AppError のサブクラスを投げ、
ここで登録する例外ハンドラーが {"detail": ..., "code": ...} の形に変換する。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"
    default_message = "リクエストが不正です"

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        self.message = message or self.default_message
        if code:
            self.code = code
        super().__init__(self.message)


class UnauthenticatedError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"
    default_message = "ログインしてください"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    default_message = "この操作を行う権限がありません"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    default_message = "対象が見つかりません"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    default_message = "他のデータと競合しています"


class BusinessRuleError(AppError):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"
    default_message = "この操作は行えません"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    default_message = "試行回数が多すぎます。しばらくしてから再度お試しください"


def _error_body(detail: str, code: str, **extra: object) -> dict[str, object]:
    return {"detail": detail, "code": code, **extra}


async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.message, exc.code))


async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body("入力内容に誤りがあります", "VALIDATION_ERROR", errors=errors),
    )


async def _handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(
        exc.status_code, "HTTP_ERROR"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(str(exc.detail), code),
        headers=getattr(exc, "headers", None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
