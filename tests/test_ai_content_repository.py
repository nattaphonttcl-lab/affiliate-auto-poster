from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.ai_content_repository import AIContentRepository
from app.schemas.ai_content import (
    PromptCategory,
    PromptTemplateCreateRequest,
    PromptTemplateStatus,
    PromptVariableRead,
)


def _template_payload() -> PromptTemplateCreateRequest:
    return PromptTemplateCreateRequest(
        name="Facebook Affiliate v1",
        category=PromptCategory.FACEBOOK,
        system_prompt="You are an affiliate copywriter for {{platform}}.",
        user_prompt="Write for {{product_name}} at {{price}} for {{target_audience}}.",
        variables=[
            PromptVariableRead(name="product_name"),
            PromptVariableRead(name="price"),
            PromptVariableRead(name="target_audience"),
            PromptVariableRead(name="platform"),
        ],
        temperature=Decimal("0.70"),
        max_tokens=800,
        version=1,
        status=PromptTemplateStatus.ACTIVE,
    )


def test_prompt_template_crud_and_provider_config(db_session: Session) -> None:
    repository = AIContentRepository(db_session)

    created = repository.create_template(payload=_template_payload(), created_by=1)
    assert created.id > 0
    assert created.category == PromptCategory.FACEBOOK.value
    assert created.variables == ["product_name", "price", "target_audience", "platform"]

    templates = repository.list_templates(
        category=PromptCategory.FACEBOOK,
        status=PromptTemplateStatus.ACTIVE,
    )
    assert len(templates) == 1

    config = repository.upsert_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        api_key="super-secret-key",
        encryption_key="test-encryption-key",
        base_url=None,
        is_active=True,
    )
    assert config.id > 0

    decrypted = repository.decrypt_provider_api_key(
        config=config,
        encryption_key="test-encryption-key",
    )
    assert decrypted == "super-secret-key"
