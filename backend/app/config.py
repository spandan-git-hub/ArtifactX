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
    log_level: str = "INFO"

    # PostgreSQL Database - Configure via environment variable
    # Format: postgresql://user:password@host:port/database
    database_url: str = "postgresql://artifactx:artifactx_password@localhost:5432/artifactx"

    # Test Database URL (defaults to in-memory SQLite; isolated from production)
    test_database_url: str = "sqlite+pysqlite:///:memory:"

    # Upload Limits (in bytes, default 256 MiB = 268435456 bytes; DEC-009)
    # Memory footprint for in-memory analysis is ~2-3x file size during decompression/parsing.
    max_upload_size: int = 268435456


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent.parent