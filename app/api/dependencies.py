from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.repositories.caption_repository import CaptionRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.caption_service import CaptionService
from app.services.shopee_product_service import ShopeeProductService
from app.services.user_service import UserService
from app.utils.ai_caption_engine import AICaptionEngine
from app.utils.shopee_parser import ShopeeProductParser
from app.utils.shopee_validator import ShopeeProductValidator

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_settings_dependency() -> Settings:
    return get_settings()


def get_user_service(db: Session = Depends(get_db_session)) -> UserService:
    return UserService(UserRepository(db))


def get_auth_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
) -> AuthService:
    return AuthService(UserRepository(db), settings)


def get_shopee_product_service(
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
) -> ShopeeProductService:
    repository = ProductRepository(db)
    parser = ShopeeProductParser(timeout_seconds=settings.shopee_request_timeout_seconds)
    validator = ShopeeProductValidator()
    return ShopeeProductService(repository, parser, validator, settings)


def get_caption_service(db: Session = Depends(get_db_session)) -> CaptionService:
    product_repository = ProductRepository(db)
    caption_repository = CaptionRepository(db)
    engine = AICaptionEngine()
    return CaptionService(product_repository, caption_repository, engine)


def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings_dependency),
) -> int:
    subject = decode_access_token(token=token, settings=settings)
    if not subject:
        raise AppException(status_code=401, detail="Invalid or expired token")

    try:
        return int(subject)
    except ValueError as exc:
        raise AppException(status_code=401, detail="Invalid token subject") from exc
