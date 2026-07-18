from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK, summary="Login")
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    token = auth_service.login(email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)
