from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_current_user, get_session_token
from app.api.v1.presenters import to_me_response
from app.entities.user import User
from app.schemas.auth import ChangePasswordRequest, MeResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
def read_me(
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> MeResponse:
    # 初期パスワードの変更前でも呼べる（画面がどこへ誘導するかを決めるため）
    return to_me_response(service.get_account(user))


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_session_token),
    service: AuthService = Depends(get_auth_service),
) -> None:
    service.change_password(
        user,
        current_token=token,
        current_password=body.current_password,
        new_password=body.new_password,
    )
