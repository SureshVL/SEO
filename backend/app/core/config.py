from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OMNI-RANK OR-1"
    environment: str = "dev"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")
    firecrawl_api_key: str = Field(default="", alias="FIRECRAWL_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


settings = Settings()
