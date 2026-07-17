"""
Configuration settings for the application
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_env: str = Field(default="development", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./ct200.db",
        env="DATABASE_URL"
    )
    
    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        env="MONGODB_URI"
    )
    mongodb_database: str = Field(
        default="triage",
        env="MONGODB_DATABASE"
    )
    
    # LLM
    llm_provider: str = Field(default="groq", env="LLM_PROVIDER")
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    llm_model: str = Field(default="llama-3.1-8b-instant", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.3, env="LLM_TEMPERATURE")
    max_llm_retries: int = Field(default=3, env="MAX_LLM_RETRIES")
    
    # Versioning
    version_match_threshold: int = Field(default=85, env="VERSION_MATCH_THRESHOLD")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create a global settings object that can be imported
settings = Settings()