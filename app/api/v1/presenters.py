"""service の結果（entities）を API のレスポンス（schemas）に変換する。"""

from app.schemas.auth import MeResponse, OrganizationResponse
from app.services.auth_service import Account


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
