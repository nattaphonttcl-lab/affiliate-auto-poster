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

    secret_key: str = Field(default="change-me")
    access_token_expire_minutes: int = Field(default=60)
    jwt_algorithm: str = Field(default="HS256")

    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
