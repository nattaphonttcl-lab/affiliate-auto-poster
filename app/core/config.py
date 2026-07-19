from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Affiliate Auto Poster API")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    api_v1_prefix: str = Field(default="/api/v1")
    single_user_mode: bool = Field(default=False)

    database_url: str = Field(default="sqlite:///./affiliate.db")
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)
    db_pool_recycle_seconds: int = Field(default=1800)

    shopee_cache_ttl_minutes: int = Field(default=60)
    shopee_request_timeout_seconds: float = Field(default=10.0)
    image_output_dir: str = Field(default="generated_images")
    image_request_timeout_seconds: float = Field(default=10.0)
    image_storage_backend: str = Field(default="local")
    image_storage_local_dir: str = Field(default="generated_images")
    image_storage_bucket: str | None = Field(default=None)
    image_storage_endpoint: str | None = Field(default=None)
    image_template_cache_ttl_seconds: int = Field(default=300)
    image_provider_failover_order: str = Field(
        default="local_template,openai,google_imagen,stability_ai,flux"
    )
    image_provider_encryption_key: str = Field(default="change-me-image-provider")
    image_provider_encryption_key_file: str | None = Field(default=None)
    image_min_resolution_width: int = Field(default=512)
    image_min_resolution_height: int = Field(default=512)
    image_max_upload_size_mb: int = Field(default=10)

    google_imagen_api_key: str | None = Field(default=None)
    stability_ai_api_key: str | None = Field(default=None)
    flux_api_key: str | None = Field(default=None)

    scheduler_publisher_mode: str = Field(default="audit")
    scheduler_webhook_url: str | None = Field(default=None)
    scheduler_webhook_timeout_seconds: float = Field(default=10.0)

    publishing_provider_failover_order: str = Field(
        default="facebook,facebook_page,instagram,threads,tiktok,youtube_shorts,shopee_video"
    )
    publishing_retry_base_seconds: int = Field(default=30)
    publishing_retry_max_seconds: int = Field(default=3600)
    publishing_circuit_breaker_failures: int = Field(default=3)
    publishing_circuit_breaker_seconds: int = Field(default=120)

    secret_key: str = Field(default="change-me")
    secret_key_file: str | None = Field(default=None)
    access_token_expire_minutes: int = Field(default=60)
    jwt_algorithm: str = Field(default="HS256")
    initial_admin_email: str = Field(default="admin@example.com")
    initial_admin_password: str = Field(default="ChangeMe123!")
    initial_admin_password_file: str | None = Field(default=None)

    cors_allowed_origins: str = Field(
        default=(
            "http://localhost:3000,http://localhost:5173,"
            "http://127.0.0.1:3000,http://127.0.0.1:5173"
        )
    )
    cors_allow_credentials: bool = Field(default=True)
    rate_limit_requests_per_minute: int = Field(default=120)

    security_csp: str = Field(
        default=(
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "font-src 'self' data:; "
            "connect-src 'self' http: https: ws: wss:"
        )
    )
    security_hsts_enabled: bool = Field(default=False)
    security_hsts_max_age: int = Field(default=31536000)

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    tracing_enabled: bool = Field(default=False)
    tracing_service_name: str = Field(default="affiliate-auto-poster-backend")
    tracing_otlp_endpoint: str | None = Field(default=None)

    ai_provider_encryption_key: str = Field(default="change-me-ai-credentials")
    ai_provider_encryption_key_file: str | None = Field(default=None)
    ai_template_cache_ttl_seconds: int = Field(default=300)
    ai_generation_rate_limit_per_minute: int = Field(default=30)
    ai_banned_words: str = Field(default="scam,fake,guaranteed rich")

    openai_api_key: str | None = Field(default=None)
    openai_api_key_file: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    gemini_api_key_file: str | None = Field(default=None)
    claude_api_key: str | None = Field(default=None)
    claude_api_key_file: str | None = Field(default=None)
    deepseek_api_key: str | None = Field(default=None)
    deepseek_api_key_file: str | None = Field(default=None)
    openrouter_api_key: str | None = Field(default=None)
    openrouter_api_key_file: str | None = Field(default=None)

    redis_url: str = Field(default="redis://redis:6379/0")
    redis_enabled: bool = Field(default=False)
    api_cache_ttl_seconds: int = Field(default=60)
    image_cache_ttl_seconds: int = Field(default=3600)

    minio_endpoint: str | None = Field(default="minio:9000")
    minio_access_key: str | None = Field(default="minioadmin")
    minio_access_key_file: str | None = Field(default=None)
    minio_secret_key: str | None = Field(default="minioadmin")
    minio_secret_key_file: str | None = Field(default=None)
    minio_bucket_name: str = Field(default="affiliate-assets")
    minio_secure: bool = Field(default=False)

    workers_poll_seconds: int = Field(default=10)
    workers_default_owner_user_id: int = Field(default=1)

    @model_validator(mode="after")
    def _load_file_backed_secrets(self) -> "Settings":
        self.secret_key = self._resolve_secret(self.secret_key, self.secret_key_file)
        self.initial_admin_password = self._resolve_secret(
            self.initial_admin_password,
            self.initial_admin_password_file,
        )
        self.ai_provider_encryption_key = self._resolve_secret(
            self.ai_provider_encryption_key,
            self.ai_provider_encryption_key_file,
        )
        self.image_provider_encryption_key = self._resolve_secret(
            self.image_provider_encryption_key,
            self.image_provider_encryption_key_file,
        )
        self.openai_api_key = self._resolve_secret(
            self.openai_api_key, self.openai_api_key_file
        )
        self.gemini_api_key = self._resolve_secret(
            self.gemini_api_key, self.gemini_api_key_file
        )
        self.claude_api_key = self._resolve_secret(
            self.claude_api_key, self.claude_api_key_file
        )
        self.deepseek_api_key = self._resolve_secret(
            self.deepseek_api_key, self.deepseek_api_key_file
        )
        self.openrouter_api_key = self._resolve_secret(
            self.openrouter_api_key, self.openrouter_api_key_file
        )
        self.minio_access_key = self._resolve_secret(
            self.minio_access_key, self.minio_access_key_file
        )
        self.minio_secret_key = self._resolve_secret(
            self.minio_secret_key, self.minio_secret_key_file
        )
        self._validate_production_secrets()
        return self

    @staticmethod
    def _resolve_secret(value: str | None, path: str | None) -> str | None:
        if not path:
            return value

        content = Path(path).read_text(encoding="utf-8").strip()
        if not content:
            return value
        return content

    def _validate_production_secrets(self) -> None:
        if self.environment.lower() != "production":
            return

        insecure_values = {
            "secret_key": {"change-me"},
            "ai_provider_encryption_key": {"change-me-ai-credentials"},
            "image_provider_encryption_key": {"change-me-image-provider"},
            "initial_admin_password": {"ChangeMe123!"},
            "minio_access_key": {"minioadmin"},
            "minio_secret_key": {"minioadmin"},
        }

        invalid_fields = [
            field_name
            for field_name, disallowed in insecure_values.items()
            if getattr(self, field_name) in disallowed
        ]
        if invalid_fields:
            raise ValueError(
                "Unsafe default secrets are not allowed in production: "
                + ", ".join(sorted(invalid_fields))
            )

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_allowed_origins.split(",")]
        return [item for item in origins if item]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
