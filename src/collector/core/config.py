"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, MongoDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables prefixed with ``COLLECTOR_``."""

    model_config = SettingsConfigDict(
        env_prefix="COLLECTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ── MongoDB ───────────────────────────────────────────────────────────
    mongo_uri: MongoDsn = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI",
    )
    mongo_db: str = Field(default="contract_collector", description="Database name")
    raw_collection: str = Field(default="raw_records", description="Raw HTML / extracted records")
    canonical_collection: str = Field(
        default="canonical_records", description="Normalized canonical records"
    )

    # ── Scraping ──────────────────────────────────────────────────────────
    max_concurrency: int = Field(default=5, ge=1, description="Max concurrent browser contexts")
    rate_limit_per_domain: float = Field(
        default=2.0, ge=0.1, description="Max requests per second per domain"
    )
    request_timeout_s: int = Field(default=30, ge=5)
    max_retries: int = Field(default=3, ge=0)
    retry_backoff_base: float = Field(default=2.0, ge=1.0)

    # ── Playwright ────────────────────────────────────────────────────────
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True

    # ── Snapshots / checkpoints ───────────────────────────────────────────
    snapshot_dir: Path = Field(default=Path("data/snapshots"))
    checkpoint_dir: Path = Field(default=Path("data/checkpoints"))

    # ── Redis (optional worker queue) ─────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── ML ────────────────────────────────────────────────────────────────
    classifier_model_path: Path = Field(default=Path("models/category_classifier.pkl"))

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True, description="Emit structured JSON logs")


settings = Settings()
