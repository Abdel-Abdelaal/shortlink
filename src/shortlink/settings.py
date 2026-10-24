"""Read application settings from environment variables."""

from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated deployment settings for the application."""

    model_config = SettingsConfigDict(env_prefix="SHORTLINK_", env_file=".env")

    database_path: Path = Path("shortlink.db")
    base_url: HttpUrl = HttpUrl("http://127.0.0.1:8000")
    code_length: int = Field(default=7, ge=4, le=32)
