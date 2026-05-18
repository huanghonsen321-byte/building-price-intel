from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://building_price:building_price@127.0.0.1:5432/building_price_intel"
    vllm_base_url: str = "http://127.0.0.1:8000/v1"
    vllm_model: str = "aeon-local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
