from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    yl_database_url: str = ""
    mockup_database_url: str = ""
    mockup_cors_origins: str = "http://127.0.0.1:5174,http://localhost:5174"
    default_business_unit: str = "成人营养品事业部"
    default_business_code: str = "CRYYBU"
    flask_env: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


@lru_cache
def load_region_config() -> dict:
    path = CONFIG_DIR / "region_map.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def load_fulfillment_config() -> dict:
    path = CONFIG_DIR / "fulfillment_map.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
