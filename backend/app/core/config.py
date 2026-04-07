from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "OMNI-RANK"

    # AI Providers
    LLM_PROVIDER: str = "auto"
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None

    DEFAULT_CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    DEFAULT_GEMINI_MODEL: str = "gemini-2.0-flash"
    DEFAULT_GROQ_MODEL: str = "llama-3.3-70b-versatile"
    DEFAULT_OPENAI_MODEL: str = "gpt-4o"
    DEFAULT_PERPLEXITY_MODEL: str = "sonar-pro"

    # Data Tools
    SERPER_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    PAGESPEED_API_KEY: Optional[str] = None

    # DataForSEO
    DATAFORSEO_LOGIN: Optional[str] = None
    DATAFORSEO_PASSWORD: Optional[str] = None

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    ORCHESTRATOR_API_KEY: str = "dev-orchestrator-key-change-in-prod"
    JWT_SECRET: str = "change-this-to-a-strong-secret"

    # Frontend
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    NEXT_PUBLIC_SUPABASE_URL: Optional[str] = None
    NEXT_PUBLIC_SUPABASE_ANON_KEY: Optional[str] = None
    NEXT_PUBLIC_APP_NAME: str = "OMNI-RANK"

    # Billing
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    # Integrations
    WORDPRESS_API_URL: Optional[str] = None
    WORDPRESS_USERNAME: Optional[str] = None
    WORDPRESS_APP_PASSWORD: Optional[str] = None
    SHOPIFY_STORE_URL: Optional[str] = None
    SHOPIFY_API_KEY: Optional[str] = None
    SHOPIFY_API_SECRET: Optional[str] = None

    SEO_SCORE_THRESHOLD: float = 75.0
    MAX_FEEDBACK_ITERATIONS: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"


settings = Settings()
