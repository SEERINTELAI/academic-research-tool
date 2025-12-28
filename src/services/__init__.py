"""
Service layer for Academic Research Tool.

Contains business logic and external service integrations.
"""

from src.services.database import get_supabase_client, SupabaseClient
from src.services.auth import (
    verify_token,
    get_current_user,
    AuthError,
)

__all__ = [
    "get_supabase_client",
    "SupabaseClient",
    "verify_token",
    "get_current_user",
    "AuthError",
]

