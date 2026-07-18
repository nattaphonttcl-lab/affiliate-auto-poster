from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.api.dependencies import get_image_service
from app.repositories.image_repository import ImageRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.image import ImageTemplate
from app.services.image_service import ImageService
from app.utils.image_generator_engine import ImageGeneratorEngine


def _create_user_and_token(client: TestClient) -> str:
    client.post("/api/v1/users", json={"email": "images@example.com", "password": "StrongPass123"})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "images@example.com", "password": "StrongPass123"},
    )
    return login_response.json()["access_token"]


def _create_product(client: TestClient, token: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/products/shopee", json={"url": "https://shopee.co.id/p/headset"}, headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (500, 500), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_generate_promotional_image_api(
    client: TestClient,
    db_session: Session,
    shopee_service_with_static_parser,
    tmp_path: Path,
) -> None:
    _ = shopee_service_with_static_parser

    payloads = {
        "https://cdn.example.com/blender.jpg": _png_bytes((240, 90, 40)),
        "https://cdn.example.com/logo.png": _png_bytes((10, 120, 90)),
    }

    generator = ImageGeneratorEngine(
        output_dir=str(tmp_path),
        timeout_seconds=1.0,
        image_fetcher=lambda source: payloads[source],
    )
    service = ImageService(ProductRepository(db_session), ImageRepository(db_session), generator)

    def override_image_service() -> ImageService:
        return service

    client.app.dependency_overrides[get_image_service] = override_image_service

    try:
        token = _create_user_and_token(client)
        product_id = _create_product(client, token)

        response = client.post(
            "/api/v1/images/promotional",
            json={
                "product_id": product_id,
                "template": ImageTemplate.CLASSIC.value,
                "shop_logo_url": "https://cdn.example.com/logo.png",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["product_id"] == product_id
        assert body["template"] == ImageTemplate.CLASSIC.value
        assert body["output_format"] == "png"
        assert body["width"] == 820
        assert body["height"] == 312
        assert Path(body["image_path"]).exists()
    finally:
        client.app.dependency_overrides.pop(get_image_service, None)


def test_generate_promotional_image_missing_product(client: TestClient) -> None:
    token = _create_user_and_token(client)

    response = client.post(
        "/api/v1/images/promotional",
        json={"product_id": 999999, "template": ImageTemplate.MINIMAL.value},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
