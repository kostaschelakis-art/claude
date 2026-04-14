from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "BrandForge"
    debug: bool = False
    environment: str = "production"

    # Database
    database_url: str = "postgresql+asyncpg://brandforge:brandforge@db:5432/brandforge"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "brandforge-assets"

    # Auth / JWT
    secret_key: str = "change-me-in-production-use-a-real-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # OAuth / Google Sign-In
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_discovery_url: str = "https://accounts.google.com/.well-known/openid-configuration"
    oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/callback"

    # AI Provider Keys
    google_ai_api_key: str = ""
    openai_api_key: str = ""
    stability_api_key: str = ""

    # Default AI provider: "google", "openai", or "stability"
    default_ai_provider: str = "google"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    # Allow any GitHub Codespaces forwarded URL (*.app.github.dev) via regex
    cors_origin_regex: str = r"https://.*\.app\.github\.dev"


settings = Settings()
