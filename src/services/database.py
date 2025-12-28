"""
Supabase database client.

Provides a configured Supabase client for database operations.
"""

import logging
from functools import lru_cache
from typing import Optional

from supabase import create_client, Client

from src.config import get_settings

logger = logging.getLogger(__name__)

# Type alias for clarity
SupabaseClient = Client


@lru_cache
def get_supabase_client(use_service_role: bool = False) -> SupabaseClient:
    """
    Get a cached Supabase client instance.
    
    Args:
        use_service_role: If True, use service role key for elevated permissions.
                         Should only be used for server-side operations.
    
    Returns:
        Configured Supabase client.
    
    Raises:
        ValueError: If required configuration is missing.
    """
    settings = get_settings()
    
    if use_service_role:
        if not settings.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY not configured")
        key = settings.supabase_service_role_key
    else:
        key = settings.supabase_anon_key
    
    client = create_client(settings.supabase_url, key)
    logger.info(
        f"Supabase client created (service_role={use_service_role})"
    )
    
    return client


async def check_database_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise.
    """
    try:
        client = get_supabase_client()
        # Simple query to check connection
        result = client.table("project").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

