"""すべてのリクエストに共通する処理（セキュリティヘッダー・リクエストID・アクセスログ）。

依存の少ない「純粋な ASGI ミドルウェア」として書いている（BaseHTTPMiddleware は
例外やストリーミングの扱いに癖があるため）。
"""

import logging
import secrets
import time
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

access_logger = logging.getLogger("app.access")

# 処理中のリクエストの ID
# （ログやエラーの応答に含めて、問い合わせのときに突き合わせられるようにする）
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# 画面はすべて自分のサーバーのファイルだけを使う。インラインのスクリプトやスタイルも許可しない
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        # blob: はプロフィール画像を選んだときのプレビュー、data: は SVG 内の画像用
        "img-src 'self' blob: data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

# API 仕様書（Swagger UI）は外部の CDN からスクリプトを読み込むため、CSP を付けない
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = scope["path"].startswith(_DOCS_PATHS)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if not is_docs:
                    headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "same-origin"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                if self.hsts:
                    # HTTPS で公開しているときだけ：以後1年間は HTTPS でしか接続させない
                    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _valid_request_id(value: str) -> bool:
    return 0 < len(value) <= 64 and all(c.isalnum() or c in "-_." for c in value)


class RequestContextMiddleware:
    """リクエストID を決めて応答ヘッダー（X-Request-ID）に付け、アクセスログを1行出す。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # プロキシなどが付けた ID があれば引き継ぐ（ログに変な文字が入らないよう形式は確認する）
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _valid_request_id(incoming) else secrets.token_hex(8)
        request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            client = scope.get("client")
            # 画面のファイル（CSS・JS など）は数が多いので、API と HTML だけを記録する
            path = scope["path"]
            if path.startswith("/api/") or path.endswith((".html", "/")) or status_code >= 400:
                access_logger.info(
                    "%s %s %s %d %.0fms",
                    client[0] if client else "-",
                    scope["method"],
                    path,
                    status_code,
                    elapsed_ms,
                )
