import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# 存在しないメールアドレスでログインされたときにも同じ時間をかけて検証し、
# 応答時間の差から「登録済みのメールアドレスかどうか」を推測されないようにする
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-equalization")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """DB にはトークンそのものではなくハッシュ値を保存する（DB が漏れても悪用されないように）。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
