from functools import lru_cache

from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "RiskPulse AI API"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://riskpulse:riskpulse@localhost:5432/riskpulse"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    news_rss_url: str | None = None
    reddit_api_base_url: str = "https://oauth.reddit.com"
    reddit_access_token: SecretStr | None = None
    reddit_user_agent: str = "RiskPulseAI/0.1 (demo; contact=unset)"
    reddit_subreddits: list[str] = Field(default_factory=lambda: ["finance", "investing"])
    reddit_search_terms: list[str] = Field(default_factory=list)
    ingestion_api_key: SecretStr | None = None
    ingestion_batch_size: int = Field(default=25, ge=1, le=100)
    ingestion_poll_interval_seconds: int = Field(default=300, ge=1, le=86_400)
    ingestion_request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    ingestion_max_retries: int = Field(default=2, ge=0, le=5)
    ingestion_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=30)

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
