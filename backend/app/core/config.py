from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    environment: str = "dev"
    log_level: str = "INFO"
    app_name: str = "OMNI-RANK"
    llm_provider: str = "auto"
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    default_claude_model: str = "claude-sonnet-4-20250514"
    default_gemini_model: str = "gemini-2.0-flash"
    default_groq_model: str = "llama-3.3-70b-versatile"
    default_openai_model: str = "gpt-4o"
    default_perplexity_model: str = "sonar-pro"
    serper_api_key: str = ""
    firecrawl_api_key: str = ""
    pagespeed_api_key: str = ""
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    redis_url: str = ""
    orchestrator_api_key: str = "dev-orchestrator-key"
    orchestrator_keys_json: str = ""
    jwt_secret: str = "change-this-to-a-strong-secret"
    cors_origins: str = "*"
    rate_limit_per_minute: int = 60
    job_store_path: str = "omnirank_jobs.db"
    seo_score_threshold: float = 75.0
    max_feedback_iterations: int = 3
    resend_api_key: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    wordpress_deploy_webhook: str = ""
    shopify_deploy_webhook: str = ""
    appstore_deploy_webhook: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
