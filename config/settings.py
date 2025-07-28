"""
Configuration management for the multi-agent research pipeline.
"""

import os
from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # LLM Configuration
    llm_provider: Literal["openai", "gemini"] = Field(default="gemini")
    
    # OpenAI Settings
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4o")
    
    # Gemini Settings  
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-1.5-pro")
    
    # Search API Settings
    tavily_api_key: Optional[str] = Field(default=None)
    serp_api_key: Optional[str] = Field(default=None)
    
    # Gmail Settings
    gmail_credentials_path: str = Field(default="./credentials/credentials.json")
    
    # Search Strategy Configuration
    search_strategy: Literal["tavily_only", "serp_only", "intelligent"] = Field(default="intelligent")
    max_search_results: int = Field(default=10, ge=1, le=50)
    search_timeout: int = Field(default=30, ge=5, le=120)
    
    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_file: str = Field(default="./logs/research_agent.log")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class AgentDependencies(BaseModel):
    """Dependencies injection for agents."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    settings: Settings
    tavily_api_key: Optional[str] = None
    serp_api_key: Optional[str] = None
    gmail_credentials_path: str = "./credentials/credentials.json"
    
    def __init__(self, **data):
        settings = Settings()
        super().__init__(
            settings=settings,
            tavily_api_key=settings.tavily_api_key,
            serp_api_key=settings.serp_api_key,
            gmail_credentials_path=settings.gmail_credentials_path,
            **data
        )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def validate_api_keys(settings: Settings) -> None:
    """Validate that required API keys are present."""
    errors = []
    
    # Check LLM provider keys
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required when using OpenAI provider")
    elif settings.llm_provider == "gemini" and not settings.gemini_api_key:
        errors.append("GEMINI_API_KEY is required when using Gemini provider")
    
    # Check search API keys based on strategy
    if settings.search_strategy in ["tavily_only", "intelligent"] and not settings.tavily_api_key:
        errors.append("TAVILY_API_KEY is required for tavily_only or intelligent search strategy")
    
    if settings.search_strategy in ["serp_only", "intelligent"] and not settings.serp_api_key:
        errors.append("SERP_API_KEY is required for serp_only or intelligent search strategy")
    
    # Check Gmail credentials (optional for search-only operations)
    # if not Path(settings.gmail_credentials_path).exists():
    #     errors.append(f"Gmail credentials file not found at {settings.gmail_credentials_path}")
    
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))


def setup_logging(settings: Settings) -> None:
    """Setup logging configuration."""
    import logging
    import os
    
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler()
        ]
    )


# Global settings instance
settings = get_settings()