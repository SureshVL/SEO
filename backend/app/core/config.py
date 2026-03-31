from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OMNI-RANK OR-1"
    environment: str = "dev"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    serper_api_key: str = ""
    firecrawl_api_key: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    orchestrator_api_key: str = "dev-orchestrator-key"
    job_store_path: str = "./.omnirank_jobs.db"
    log_level: str = "INFO"

    seo_score_threshold: float = 95.0
    max_feedback_iterations: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
