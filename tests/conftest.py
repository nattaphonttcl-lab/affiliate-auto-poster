from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db_session, get_shopee_product_service
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models import caption, product, user  # noqa: F401
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductPayload
from app.services.shopee_product_service import ShopeeProductService


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class _StaticParser:
    def parse(self, url: str) -> ProductPayload:
        return ProductPayload(
            title="Portable Blender",
            price="149.00",
            original_price="199.00",
            discount="25%",
            rating=4.9,
            sold_count=1200,
            images=["https://cdn.example.com/blender.jpg"],
            shop_name="Kitchen Hub",
            category="Home Appliances",
            affiliate_url=url,
        )


class _PassValidator:
    def validate_url(self, url: str) -> None:
        _ = url

    def validate_payload(self, payload: ProductPayload) -> None:
        _ = payload


@pytest.fixture()
def shopee_service_with_static_parser(client: TestClient, db_session: Session) -> Generator[ShopeeProductService, None, None]:
    settings = get_settings()
    service = ShopeeProductService(ProductRepository(db_session), _StaticParser(), _PassValidator(), settings)

    def override_shopee_service() -> ShopeeProductService:
        return service

    client.app.dependency_overrides[get_shopee_product_service] = override_shopee_service
    try:
        yield service
    finally:
        client.app.dependency_overrides.pop(get_shopee_product_service, None)
