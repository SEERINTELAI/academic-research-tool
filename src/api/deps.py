"""
FastAPI dependencies.

Common dependencies used across API routes.
"""

from typing import Annotated

from fastapi import Depends

from src.config import Settings, get_settings
from src.models.common import UserContext
from src.services.auth import get_current_user, get_optional_user
from src.services.database import SupabaseClient, get_supabase_client

# Type aliases for cleaner dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[UserContext, Depends(get_current_user)]
OptionalUser = Annotated[UserContext | None, Depends(get_optional_user)]


def get_db() -> SupabaseClient:
    """Get Supabase client for database operations."""
    return get_supabase_client()


def get_service_db() -> SupabaseClient:
    """Get Supabase client with service role (elevated permissions)."""
    return get_supabase_client(use_service_role=True)


DatabaseDep = Annotated[SupabaseClient, Depends(get_db)]
ServiceDatabaseDep = Annotated[SupabaseClient, Depends(get_service_db)]

