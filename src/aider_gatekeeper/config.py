"""Configuration for Aider-Gatekeeper."""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Engine URLs
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    llamacpp_url: str = os.getenv("LLAMACPP_URL", "http://localhost:8080")

    # Token Truncation
    max_tokens: int = int(os.getenv("MAX_TOKENS", "9500"))
    default_model: str = os.getenv("DEFAULT_MODEL", "Qwen/Qwen2.5-7B")

    # App Settings
    app_name: str = "Aider-Gatekeeper"
    version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
