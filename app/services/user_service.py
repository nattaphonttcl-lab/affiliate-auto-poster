from app.core.exceptions import AppException
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepositoryProtocol


class UserService:
    def __init__(self, user_repository: UserRepositoryProtocol) -> None:
        self._user_repository = user_repository

    def create_user(self, *, email: str, password: str) -> User:
        existing = self._user_repository.get_by_email(email)
        if existing:
            raise AppException(status_code=409, detail="Email is already registered")

        return self._user_repository.create(email=email, hashed_password=hash_password(password))

    def list_users(self) -> list[User]:
        return self._user_repository.list()

    def get_user_or_404(self, user_id: int) -> User:
        user = self._user_repository.get_by_id(user_id)
        if not user:
            raise AppException(status_code=404, detail="User not found")
        return user

    def update_user_status(self, *, user_id: int, is_active: bool) -> User:
        user = self.get_user_or_404(user_id)
        user.is_active = is_active
        return self._user_repository.update(user)
