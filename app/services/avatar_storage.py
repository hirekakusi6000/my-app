"""プロフィール画像のファイル保存。

- 受け付けるのは PNG / JPEG / WebP の 2MB まで。拡張子や Content-Type ではなく、
  ファイルの先頭のバイト列（マジックナンバー）で形式を判定する。
- 保存するファイル名は推測できないランダムな名前にし、利用者が付けた名前は使わない。
"""

import re
import secrets
from pathlib import Path

from app.core.errors import BusinessRuleError

MAX_AVATAR_BYTES = 2 * 1024 * 1024

_MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}
_FILENAME = re.compile(r"^[0-9a-f]{32}\.(png|jpg|webp)$")


def detect_image_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


class AvatarStorage:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def save(self, data: bytes) -> str:
        if len(data) > MAX_AVATAR_BYTES:
            raise BusinessRuleError("画像のサイズは2MBまでです", code="FILE_TOO_LARGE")
        ext = detect_image_type(data)
        if ext is None:
            raise BusinessRuleError(
                "PNG / JPEG / WebP の画像を選んでください", code="UNSUPPORTED_FILE_TYPE"
            )
        filename = f"{secrets.token_hex(16)}.{ext}"
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / filename).write_bytes(data)
        return filename

    def path(self, filename: str) -> Path:
        # DB の値をそのままパスにしない（念のため、想定した形式の名前だけを許可する）
        if not _FILENAME.match(filename):
            raise ValueError(f"不正なファイル名です: {filename!r}")
        return self.directory / filename

    def delete(self, filename: str | None) -> None:
        if filename:
            self.path(filename).unlink(missing_ok=True)

    @staticmethod
    def media_type(filename: str) -> str:
        return _MEDIA_TYPES[filename.rsplit(".", 1)[1]]
