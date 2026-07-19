from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import (
    get_auth_service,
    get_current_user_id_allow_password_change,
)
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
)
def login(
    payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    token = auth_service.login(email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
)
def change_password(
    payload: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id_allow_password_change),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    auth_service.change_password(
        user_id=user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
