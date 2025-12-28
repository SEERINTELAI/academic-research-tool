"""
Application configuration using Pydantic Settings.

Environment variables are loaded from .env file or system environment.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Academic Research Tool"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous/public key")
    supabase_service_role_key: Optional[str] = Field(
        default=None, 
        description="Supabase service role key (for server-side operations)"
    )
    supabase_jwt_secret: Optional[str] = Field(
        default=None,
        description="Supabase JWT secret for token verification"
    )
    
    # Hyperion RAG
    hyperion_mcp_url: str = Field(
        default="https://n8n-dev-u36296.vm.elestio.app/mcp/hyperion",
        description="Hyperion MCP endpoint URL"
    )
    hyperion_auth_header: Optional[str] = Field(
        default=None,
        description="Authorization header value for Hyperion MCP"
    )
    
    # Claude API
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude"
    )
    claude_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use"
    )
    
    # External APIs
    semantic_scholar_api_key: Optional[str] = Field(
        default=None,
        description="Semantic Scholar API key (optional, increases rate limit)"
    )
    grobid_url: str = Field(
        default="https://kermitt2-grobid.hf.space",
        description="GROBID service URL for PDF parsing"
    )
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to avoid re-reading environment on every call.
    """
    return Settings()

