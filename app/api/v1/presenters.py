"""service の結果（entities）を API のレスポンス（schemas）に変換する。"""

from app.schemas.auth import MeResponse, OrganizationResponse
from app.services.auth_service import Account


def avatar_url(user_id: int, avatar_path: str | None) -> str | None:
    """プロフィール画像の URL。

    ファイル名が変わると URL も変わるので、画像を変えたときにブラウザの古いキャッシュが使われない。
    """
    if not avatar_path:
        return None
    return f"/api/v1/users/{user_id}/avatar?v={avatar_path[:8]}"


def to_me_response(account: Account) -> MeResponse:
    user = account.user
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        must_change_password=user.must_change_password,
        profile_completed=account.profile_completed,
        organization=OrganizationResponse(
            id=account.organization.id, name=account.organization.name
        ),
    )
