from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import UserRepositoryProtocol


class AuthService:
    def __init__(self, user_repository: UserRepositoryProtocol, settings: Settings) -> None:
        self._user_repository = user_repository
        self._settings = settings

    def login(self, *, email: str, password: str) -> str:
        user = self._user_repository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AppException(status_code=401, detail="Invalid credentials")

        if not user.is_active:
            raise AppException(status_code=403, detail="User is inactive")

        return create_access_token(subject=str(user.id), settings=self._settings)
