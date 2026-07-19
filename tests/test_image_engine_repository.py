from sqlalchemy.orm import Session

from app.repositories.image_engine_repository import ImageEngineRepository
from app.schemas.image_engine import (
    ImageTemplateCreateRequest,
    ImageTemplateStatus,
    ImageTemplateUpdateRequest,
    ImageType,
)


def _template_payload() -> ImageTemplateCreateRequest:
    return ImageTemplateCreateRequest(
        name="Facebook Cover V1",
        image_type=ImageType.FACEBOOK_COVER,
        canvas_width=820,
        canvas_height=312,
        safe_area={"x": 20, "y": 20, "width": 780, "height": 272},
        background={"type": "solid", "color": "#ffffff"},
        layers=[{"name": "title"}, {"name": "price"}],
        fonts={"title": "DejaVuSans-Bold.ttf"},
        colors={"title": "#111111"},
        logo_position={"x": 700, "y": 16, "width": 96, "height": 96},
        watermark={"enabled": True, "text": "Affiliate"},
        overlay={"enabled": False},
        dynamic_variables=["product_name", "price", "caption"],
        version=1,
        status=ImageTemplateStatus.ACTIVE,
    )


def test_image_template_and_provider_config_crud(db_session: Session) -> None:
    repository = ImageEngineRepository(db_session)

    created = repository.create_template(payload=_template_payload(), created_by=1)
    assert created.id > 0

    templates = repository.list_templates(
        image_type=ImageType.FACEBOOK_COVER,
        status=ImageTemplateStatus.ACTIVE,
    )
    assert len(templates) == 1

    updated = repository.update_template(
        template_id=created.id,
        payload=ImageTemplateUpdateRequest(status=ImageTemplateStatus.INACTIVE),
    )
    assert updated is not None

    config = repository.upsert_provider_config(
        provider="openai",
        model="gpt-image-1",
        api_key="img-secret",
        encryption_key="image-test-key",
        base_url=None,
        is_active=True,
    )
    decrypted = repository.decrypt_provider_api_key(
        config=config,
        encryption_key="image-test-key",
    )
    assert decrypted == "img-secret"

    assert repository.delete_template(template_id=created.id) is True
