from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    FIRECRAWL_WEBHOOK_SECRET: str

    DATABASE_URL: str = "sqlite:///./local.db"

    QDRANT_URL: str = "qdrant_url"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "finnish_tax_law"

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_MINI: str = "gpt-4o-mini"
    OPENAI_MODEL_FULL: str = "gpt-4o"


settings = Settings()
