import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.log_config import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import RateLimiter
from app.db import migrate

logger = logging.getLogger("app")


class FrontendFiles(StaticFiles):
    """画面ファイルの配信。

    - 複数のフォルダを順番に探す（Vue のビルド結果 web/dist → まだ移行していない frontend/）。
      同じ URL のファイルがあれば、先に見つかったものを返す
    - 更新したファイルが確実に反映されるよう、毎回ブラウザに確認させる。
      no-cache は「使う前にサーバーへ確認する」という意味で、変更がなければ 304 が返るので軽い
    """

    def __init__(self, *, directories: list[Path], **kwargs) -> None:  # type: ignore[no-untyped-def]
        # 最後のフォルダ（frontend/）を基本とし、それより前のフォルダを優先して探す。
        # 優先するフォルダは、まだなくてもよい（起動した後にビルドしても反映される）
        super().__init__(directory=directories[-1], **kwargs)
        preferred = [str(d) for d in directories[:-1]]
        self.all_directories = [*preferred, *self.all_directories]

    def file_response(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_file)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 起動時に未適用のマイグレーションを適用する
        applied = migrate.run(settings.database_path, settings.migrations_dir)
        if applied:
            logger.info(
                "マイグレーションを適用しました: %s", ", ".join(f"{v:04d}" for v in applied)
            )
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        if not settings.cookie_secure:
            logger.warning(
                "APP_COOKIE_SECURE が false です。HTTPS で公開する場合は true にしてください"
            )
        yield

    docs = settings.enable_api_docs
    app = FastAPI(
        title="オフィス座席・従業員管理システム",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.settings = settings
    app.state.rate_limiter = RateLimiter()

    register_exception_handlers(app)
    # 後から追加したものが外側になる。リクエストID とアクセスログはいちばん外側で扱う
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.cookie_secure)
    app.add_middleware(RequestContextMiddleware)

    # API を先に登録し、残りのパスを画面ファイルの配信に回す
    app.include_router(api_router)
    if not settings.web_dist_dir.is_dir():
        logger.warning(
            "Vue の画面のビルド結果（%s）がありません。"
            "cd web && npm install && npm run build を実行してください",
            settings.web_dist_dir,
        )
    app.mount(
        "/",
        FrontendFiles(directories=[settings.web_dist_dir, settings.frontend_dir], html=True),
        name="frontend",
    )
    return app


app = create_app()
