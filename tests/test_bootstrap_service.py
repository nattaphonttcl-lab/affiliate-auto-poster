from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import verify_password
from app.db.base import Base
import app.models.ai_content  # noqa: F401
import app.models.analytics_event  # noqa: F401
import app.models.caption  # noqa: F401
import app.models.image_generation  # noqa: F401
import app.models.outbox_event  # noqa: F401
import app.models.product  # noqa: F401
import app.models.promotional_image  # noqa: F401
import app.models.publishing  # noqa: F401
import app.models.saas  # noqa: F401
import app.models.scheduled_post  # noqa: F401
import app.models.user  # noqa: F401
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


def test_bootstrap_fails_when_schema_is_missing(db_session: Session) -> None:
    settings = get_settings()

    Base.metadata.drop_all(bind=db_session.get_bind())

    with pytest.raises(RuntimeError, match="Run alembic upgrade head"):
        BootstrapService(lambda: db_session, settings).run()


def test_production_settings_reject_default_secrets() -> None:
    with pytest.raises(ValueError, match="Unsafe default secrets"):
        Settings(environment="production")


def test_production_settings_accept_file_backed_secrets(tmp_path: Path) -> None:
    secret_file = tmp_path / "secret-key.txt"
    admin_password_file = tmp_path / "admin-password.txt"
    ai_key_file = tmp_path / "ai-encryption.txt"
    image_key_file = tmp_path / "image-encryption.txt"
    minio_access_file = tmp_path / "minio-access.txt"
    minio_secret_file = tmp_path / "minio-secret.txt"

    secret_file.write_text("prod-secret-key-1234567890", encoding="utf-8")
    admin_password_file.write_text("ProdAdminPass123!", encoding="utf-8")
    ai_key_file.write_text("prod-ai-encryption-key", encoding="utf-8")
    image_key_file.write_text("prod-image-encryption-key", encoding="utf-8")
    minio_access_file.write_text("prod-minio-user", encoding="utf-8")
    minio_secret_file.write_text("prod-minio-password", encoding="utf-8")

    settings = Settings(
        environment="production",
        secret_key_file=str(secret_file),
        initial_admin_password_file=str(admin_password_file),
        ai_provider_encryption_key_file=str(ai_key_file),
        image_provider_encryption_key_file=str(image_key_file),
        minio_access_key_file=str(minio_access_file),
        minio_secret_key_file=str(minio_secret_file),
    )

    assert settings.secret_key == "prod-secret-key-1234567890"
    assert settings.initial_admin_password == "ProdAdminPass123!"
