"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ArtifactX"
    debug: bool = False

    # PostgreSQL Database - Configure via environment variable
    # Format: postgresql://user:password@host:port/database
    database_url: str = "postgresql://artifactx:artifactx_password@localhost:5432/artifactx"

    upload_dir: str = "uploads"
    max_upload_size: int = 1073741824  # 1GB in bytes
    log_level: str = "INFO"
    demo_mode: bool = False  # Enable demo mode with mock data


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure data directories exist
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / settings.upload_dir
REPORTS_DIR = BASE_DIR / "reports"

UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)