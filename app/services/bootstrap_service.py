from collections.abc import Callable

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import logger
from app.db.base import Base
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
            self._assert_required_schema(session)
            repository = UserRepository(session)
            if repository.count() > 0:
                logger.info("Initial administrator already exists.")
                return

            try:
                UserService(repository).create_user(
                    email=self._settings.initial_admin_email,
                    password=self._settings.initial_admin_password,
                )
            except IntegrityError:
                session.rollback()
                logger.info("Initial administrator already exists.")
                return

            logger.info(
                "Created initial administrator account: %s",
                self._settings.initial_admin_email,
            )
        finally:
            session.close()

    def _assert_required_schema(self, session: Session) -> None:
        inspector = inspect(session.get_bind())
        existing_tables = set(inspector.get_table_names())
        expected_tables = set(Base.metadata.tables.keys())

        if not existing_tables:
            raise RuntimeError(
                "Database schema is missing. Run alembic upgrade head before starting the application."
            )

        missing_tables = sorted(expected_tables - existing_tables)
        if missing_tables:
            raise RuntimeError(
                "Database schema is incomplete. Run alembic upgrade head before starting the application. "
                + "Missing tables: "
                + ", ".join(missing_tables)
            )
