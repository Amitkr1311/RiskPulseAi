from functools import lru_cache
from decimal import Decimal

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
    social_csv_path: str = "data/tweets-vs-stock.csv"
    reddit_api_base_url: str = "https://oauth.reddit.com"
    reddit_ingestion_enabled: bool = False
    reddit_access_token: SecretStr | None = None
    reddit_user_agent: str = "RiskPulseAI/0.1 (demo; contact=unset)"
    reddit_subreddits: list[str] = Field(default_factory=lambda: ["finance", "investing"])
    reddit_search_terms: list[str] = Field(default_factory=list)
    ingestion_api_key: SecretStr | None = None
    ingestion_batch_size: int = Field(default=25, ge=1, le=100)
    ingestion_poll_interval_seconds: int = Field(default=300, ge=1, le=86_400)
    ingestion_live_enabled: bool = False
    ingestion_live_sources: list[str] = Field(default_factory=lambda: ["news", "social", "reddit"])
    ingestion_live_process_nlp: bool = True
    ingestion_request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    ingestion_max_retries: int = Field(default=2, ge=0, le=5)
    ingestion_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=30)
    nlp_sentiment_backend: str = "heuristic"
    nlp_sentiment_model_id: str = "ProsusAI/finbert"
    nlp_allow_model_download: bool = False
    nlp_model_device: str = "cpu"
    nlp_max_text_chars: int = Field(default=12_000, ge=500, le=100_000)
    nlp_batch_size: int = Field(default=25, ge=1, le=100)
    replay_default_speed: float = Field(default=1.0, gt=0, le=100)
    replay_max_speed: float = Field(default=10.0, gt=0, le=100)
    replay_default_batch_size: int = Field(default=1, ge=1, le=100)
    nlp_entity_aliases_path: str = "data/entity_aliases.json"
    research_reports_dir: str = "research/reports"
    research_market_data_dir: str = "research/market_data"
    # A strict greater-than comparison is used by automatic stress triggers.
    # Keep the older name as an input alias for existing local environments.
    stress_trigger_threshold: int = Field(default=7, ge=1, le=9)
    stress_impact_threshold: int | None = Field(default=None, ge=1, le=9)
    stress_model_version: str = "stress-v1"
    stress_reconciliation_tolerance: Decimal = Field(default=Decimal("0.01"), ge=Decimal("0"), le=Decimal("1"))

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def model_post_init(self, __context: object) -> None:
        if (
            self.stress_impact_threshold is not None
            and "stress_trigger_threshold" not in self.model_fields_set
        ):
            self.stress_trigger_threshold = self.stress_impact_threshold
        self.stress_impact_threshold = self.stress_trigger_threshold


@lru_cache
def get_settings() -> Settings:
    return Settings()
