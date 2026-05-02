"""
Configuration settings for SmartShift application.
Loads environment variables and provides centralized configuration management.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # IBM watsonx.ai Configuration
    watsonx_api_key: str = Field(default="", env="WATSONX_API_KEY")
    watsonx_project_id: str = Field(default="", env="WATSONX_PROJECT_ID")
    watsonx_url: str = Field(
        default="https://us-south.ml.cloud.ibm.com",
        env="WATSONX_URL"
    )
    
    # ChromaDB Configuration
    chroma_persist_dir: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIR")
    chroma_collection_name: str = Field(
        default="worker_skills",
        env="CHROMA_COLLECTION_NAME"
    )
    
    # Embedding Model Configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    
    # LLM Configuration
    llm_model: str = Field(
        default="ibm/granite-13b-chat-v2",
        env="LLM_MODEL"
    )
    llm_max_tokens: int = Field(default=500, env="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    
    # Application Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    
    # Data paths
    data_dir: Path = Field(default=Path("data"))
    workers_csv_path: Path = Field(default=Path("data/workers.csv"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def validate_watsonx_credentials(self) -> bool:
        """Check if watsonx.ai credentials are configured."""
        return bool(self.watsonx_api_key and self.watsonx_project_id)
    
    def get_chroma_path(self) -> Path:
        """Get ChromaDB persistence directory as Path object."""
        return Path(self.chroma_persist_dir)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings

# Made with Bob
