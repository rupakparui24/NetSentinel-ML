"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NETSENTINEL_",
        extra="ignore",
    )

    app_name: str = "NetSentinel-ML"
    environment: str = Field(default="development")
    api_prefix: str = "/api/v1"
    api_key: str = Field(default="dev-netsentinel-key")
    rate_limit_per_minute: int = Field(default=100)
    drift_threshold: float = Field(default=0.3)

    project_root: Path = Field(default_factory=lambda: Path.cwd())
    model_registry_dir: Path = Field(default=Path("models/registry"))
    data_dir: Path = Field(default=Path("data"))
    metrics_window_size: int = Field(default=1000)

    demo_training_rows: int = Field(default=900)
    random_seed: int = Field(default=42)

    @property
    def registry_path(self) -> Path:
        return self.model_registry_dir / "registry.json"

    @property
    def reference_data_path(self) -> Path:
        return self.data_dir / "processed" / "reference_features.csv"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""

    return Settings()
