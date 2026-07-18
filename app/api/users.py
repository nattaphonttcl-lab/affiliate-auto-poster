from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id, get_user_service
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(
    payload: UserCreate, user_service: UserService = Depends(get_user_service)
) -> UserRead:
    return UserRead.model_validate(
        user_service.create_user(email=payload.email, password=payload.password)
    )


@router.get("", response_model=list[UserRead], summary="List users")
def list_users(
    _: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    users = user_service.list_users()
    return [UserRead.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserRead, summary="Get user")
def get_user(
    user_id: int,
    _: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    return UserRead.model_validate(user_service.get_user_or_404(user_id))


@router.patch("/{user_id}", response_model=UserRead, summary="Update user")
def update_user(
    user_id: int,
    payload: UserUpdate,
    _: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    if payload.is_active is None:
        return UserRead.model_validate(user_service.get_user_or_404(user_id))

    user = user_service.update_user_status(user_id=user_id, is_active=payload.is_active)
    return UserRead.model_validate(user)
