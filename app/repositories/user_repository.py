from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepositoryProtocol(Protocol):
    def get_by_id(self, user_id: int) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def list(self) -> list[User]: ...

    def create(self, *, email: str, hashed_password: str) -> User: ...

    def update(self, user: User) -> User: ...


class UserRepository(UserRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self._db.execute(stmt).scalar_one_or_none()

    def list(self) -> list[User]:
        stmt = select(User).order_by(User.id.asc())
        return list(self._db.scalars(stmt))

    def create(self, *, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
