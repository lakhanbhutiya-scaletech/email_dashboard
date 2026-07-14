from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Sales Outlook Dashboard"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    FERNET_KEY: str

    # AI Labs
    AILABS_BASE_URL: str = "http://localhost:8000/api/v1"
    AILABS_TIMEOUT_SECONDS: float = 120.0

    # Agent provisioning defaults (spec §2/§6)
    AGENT_MODEL: str = "gpt-4o"
    AGENT_TEMPERATURE: float = 0.2
    AGENT_MAX_TOKENS: int = 4096
    AGENT_MEMORY_WINDOW: int = 4

    # Dev: when true, run_analysis_for_employee returns generated dummy JSON
    # instead of calling AI Labs — lets the pipeline run with no Outlook connected.
    DUMMY_ANALYSIS: bool = False

    # Cron
    CRON_ENABLED: bool = True
    CRON_INTERVAL_MINUTES: int = 60
    CRON_STAGGER_SECONDS: float = 5.0
    ANALYSIS_TIMEZONE: str = "Asia/Kolkata"

    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
