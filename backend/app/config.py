from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    gemini_api_key: str = "not-set"
    gemini_model: str = "gemini-3.0-pro"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_max_tokens_per_minute: int = 1_000_000
    gemini_max_requests_per_minute: int = 60
    gemini_budget_per_run_usd: float = 5.00
    gemini_budget_per_ensemble_usd: float = 25.00

    # External Data Ingestion
    news_api_key: str = ""
    webhook_rate_limit_per_minute: int = 5
    max_ingested_events_per_tick: int = 20

    # Database
    database_url: str = "postgresql+asyncpg://swarmscope:changeme@localhost:5432/swarmscope"
    postgres_password: str = "changeme"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me"
    cors_origins: str = "http://localhost:4200"
    max_upload_size_mb: int = 50
    upload_dir: str = "/app/uploads"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
