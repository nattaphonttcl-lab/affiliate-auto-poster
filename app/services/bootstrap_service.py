from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import logger
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class BootstrapService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    def run(self) -> None:
        session = self._session_factory()
        try:
            User.__table__.create(bind=session.get_bind(), checkfirst=True)
            repository = UserRepository(session)
            if repository.count() > 0:
                logger.info("Initial administrator already exists.")
                return

            UserService(repository).create_user(
                email=self._settings.initial_admin_email,
                password=self._settings.initial_admin_password,
            )
            logger.info(
                "Created initial administrator account: %s",
                self._settings.initial_admin_email,
            )
        finally:
            session.close()
