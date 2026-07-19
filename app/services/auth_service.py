from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepositoryProtocol


class AuthService:
    def __init__(
        self, user_repository: UserRepositoryProtocol, settings: Settings
    ) -> None:
        self._user_repository = user_repository
        self._settings = settings

    def login(self, *, email: str, password: str) -> str:
        user = self._user_repository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AppException(status_code=401, detail="Invalid credentials")

        if not user.is_active:
            raise AppException(status_code=403, detail="User is inactive")

        return create_access_token(
            subject=str(user.id),
            settings=self._settings,
            extra_claims={
                "must_change_password": self._must_change_password(
                    user.email,
                    user.hashed_password,
                )
            },
        )

    def change_password(
        self, *, user_id: int, current_password: str, new_password: str
    ) -> None:
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise AppException(status_code=404, detail="User not found")

        if not verify_password(current_password, user.hashed_password):
            raise AppException(status_code=401, detail="Invalid credentials")

        if current_password == new_password:
            raise AppException(
                status_code=422,
                detail="New password must be different from the current password",
            )

        user.hashed_password = hash_password(new_password)
        self._user_repository.update(user)

    def _must_change_password(self, email: str, hashed_password: str) -> bool:
        if email.casefold() != self._settings.initial_admin_email.casefold():
            return False

        return verify_password(self._settings.initial_admin_password, hashed_password)
