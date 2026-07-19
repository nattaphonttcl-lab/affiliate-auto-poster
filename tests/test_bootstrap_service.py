from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.services.bootstrap_service import BootstrapService
from app.services.user_service import UserService


def test_empty_database_creates_initial_admin(db_session: Session) -> None:
    settings = get_settings()

    BootstrapService(lambda: db_session, settings).run()

    repository = UserRepository(db_session)
    user = repository.get_by_email(settings.initial_admin_email)

    assert repository.count() == 1
    assert user is not None
    assert verify_password(settings.initial_admin_password, user.hashed_password)


def test_existing_users_do_not_create_duplicate_admin(db_session: Session) -> None:
    settings = get_settings()
    user_service = UserService(UserRepository(db_session))
    user_service.create_user(email="existing@example.com", password="StrongPass123")

    BootstrapService(lambda: db_session, settings).run()

    repository = UserRepository(db_session)
    assert repository.count() == 1
    assert repository.get_by_email(settings.initial_admin_email) is None


def test_restart_does_not_recreate_admin(db_session: Session) -> None:
    settings = get_settings()
    service = BootstrapService(lambda: db_session, settings)

    service.run()
    service.run()

    repository = UserRepository(db_session)
    users = repository.list()
    assert len(users) == 1
    assert users[0].email == settings.initial_admin_email
