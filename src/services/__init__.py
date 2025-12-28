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
from src.services.ak_client import (
    AKClient,
    AKError,
    call_ak,
)
from src.services.hyperion_client import (
    HyperionClient,
    HyperionError,
    hyperion_list_documents,
    hyperion_query,
    hyperion_ingest,
    hyperion_delete,
)

__all__ = [
    # Database
    "get_supabase_client",
    "SupabaseClient",
    # Auth
    "verify_token",
    "get_current_user",
    "AuthError",
    # AK
    "AKClient",
    "AKError",
    "call_ak",
    # Hyperion
    "HyperionClient",
    "HyperionError",
    "hyperion_list_documents",
    "hyperion_query",
    "hyperion_ingest",
    "hyperion_delete",
]

