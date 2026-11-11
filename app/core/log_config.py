"""ログの設定。

出力の形式: 2026-11-07 13:44:01 INFO  app.access [3f9c2a1b7e0d4c55] 127.0.0.1 GET /api/v1/me 200 4ms
  - [] の中はリクエストID。応答ヘッダーの X-Request-ID と同じ値なので、
    利用者からの問い合わせと突き合わせられる
  - パスワードやセッションのトークンなどの秘密の値は、ログに出さない
"""

import logging
import logging.handlers
from pathlib import Path

from app.core.middleware import request_id_var

_FORMAT = "%(asctime)s %(levelname)-5s %(name)s [%(request_id)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str, log_file: Path | None) -> None:
    """アプリのログ（app.*）の出力先と形式を設定する。何度呼んでも同じ状態になる。"""
    logger = logging.getLogger("app")
    logger.setLevel(level)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
        )
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(_RequestIdFilter())
        logger.addHandler(handler)


def mask_email(email: str) -> str:
    """ログ用にメールアドレスの一部を伏せる（例: taro@example.com → ta***@example.com）。"""
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"
