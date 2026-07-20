"""
config.py
Centralized application configuration loaded from environment variables (.env).
Uses pydantic-settings so every value is typed and validated at startup.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "NutriMama AI"
    app_env: str = "development"
    debug: bool = True

    # --- Security / JWT ---
    jwt_secret_key: str = "change-this-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # --- Database ---
    database_url: str = "sqlite:///./nutrimama.db"

    # --- Generative AI ---
    ai_provider: str = "gemini"  # "gemini" or "openai"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- RAG / ChromaDB ---
    chroma_persist_dir: str = "./rag/chroma_store"
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_top_k: int = 4

    # --- File Uploads ---
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # --- CORS ---
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # --- Frontend ---
    frontend_dir: str = "../frontend"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-reading .env on every import."""
    return Settings()


settings = get_settings()
