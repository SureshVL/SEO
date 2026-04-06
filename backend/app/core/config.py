from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OMNI-RANK OR-1"
    environment: str = "dev"

    # AI
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "auto"  # "claude", "gemini", or "auto"

    # Data providers
    serper_api_key: str = ""
    firecrawl_api_key: str = ""
    pagespeed_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    # Auth & Security
    orchestrator_api_key: str = "dev-orchestrator-key"
    orchestrator_keys_json: str = "{}"
    jwt_secret: str = ""
    cors_origins: str = "http://localhost:3000"

    # Job store
    job_store_path: str = "./.omnirank_jobs.db"
    log_level: str = "INFO"

    # Deploy webhooks
    wordpress_deploy_webhook: str = ""
    shopify_deploy_webhook: str = ""
    appstore_deploy_webhook: str = ""

    # Deploy tokens
    wordpress_token: str = ""
    shopify_token: str = ""
    appstore_token: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 120

    # Workflow
    seo_score_threshold: float = 85.0
    max_feedback_iterations: int = 3

    # Redis (optional, for production caching)
    redis_url: str = ""

    # Razorpay billing
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Email (Resend)
    resend_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
