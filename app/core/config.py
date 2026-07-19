from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Affiliate Auto Poster API")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    api_v1_prefix: str = Field(default="/api/v1")

    database_url: str = Field(default="sqlite:///./affiliate.db")

    shopee_cache_ttl_minutes: int = Field(default=60)
    shopee_request_timeout_seconds: float = Field(default=10.0)
    image_output_dir: str = Field(default="generated_images")
    image_request_timeout_seconds: float = Field(default=10.0)

    scheduler_publisher_mode: str = Field(default="audit")
    scheduler_webhook_url: str | None = Field(default=None)
    scheduler_webhook_timeout_seconds: float = Field(default=10.0)

    secret_key: str = Field(default="change-me")
    access_token_expire_minutes: int = Field(default=60)
    jwt_algorithm: str = Field(default="HS256")

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    tracing_enabled: bool = Field(default=False)
    tracing_service_name: str = Field(default="affiliate-auto-poster-backend")
    tracing_otlp_endpoint: str | None = Field(default=None)

    ai_provider_encryption_key: str = Field(default="change-me-ai-credentials")
    ai_template_cache_ttl_seconds: int = Field(default=300)
    ai_generation_rate_limit_per_minute: int = Field(default=30)
    ai_banned_words: str = Field(default="scam,fake,guaranteed rich")

    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    claude_api_key: str | None = Field(default=None)
    deepseek_api_key: str | None = Field(default=None)
    openrouter_api_key: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
