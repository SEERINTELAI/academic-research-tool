"""
Authentication service for Supabase JWT validation.

Validates JWT tokens from Supabase Auth and extracts user context.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import get_settings
from src.models.common import UserContext

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Authentication error."""
    
    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


def verify_token(token: str) -> dict:
    """
    Verify and decode a Supabase JWT token.
    
    Args:
        token: JWT token string (without 'Bearer ' prefix)
    
    Returns:
        Decoded token payload.
    
    Raises:
        AuthError: If token is invalid or expired.
    """
    settings = get_settings()
    
    if not settings.supabase_jwt_secret:
        # In development, we might not have the secret
        # Fall back to just decoding without verification
        if settings.is_development:
            logger.warning("JWT secret not configured, skipping verification in development")
            
            # For demo tokens (non-JWT format), create a mock payload
            if not token.startswith("eyJ"):
                logger.info(f"Using demo token for development: {token[:20]}...")
                return {
                    "sub": f"demo-user-{token[:8]}",
                    "email": "demo@example.com",
                    "role": "authenticated",
                }
            
            try:
                # Decode without verification - ONLY for development
                # jose.jwt.decode requires a key, so we use a dummy one
                payload = jwt.decode(
                    token, 
                    key="dummy-key-for-dev",
                    options={"verify_signature": False}
                )
                return payload
            except JWTError as e:
                raise AuthError(f"Invalid token format: {e}", "invalid_token")
        else:
            raise AuthError("JWT secret not configured", "config_error")
    
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired", "token_expired")
    except jwt.JWTClaimsError as e:
        raise AuthError(f"Invalid token claims: {e}", "invalid_claims")
    except JWTError as e:
        raise AuthError(f"Invalid token: {e}", "invalid_token")


def extract_user_context(payload: dict) -> UserContext:
    """
    Extract user context from decoded JWT payload.
    
    Args:
        payload: Decoded JWT payload.
    
    Returns:
        UserContext with user information.
    """
    # Supabase JWT structure
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Token missing user ID (sub claim)", "invalid_token")
    
    # Extract email from user_metadata or email claim
    email = payload.get("email")
    if not email:
        user_metadata = payload.get("user_metadata", {})
        email = user_metadata.get("email")
    
    # Extract role
    role = payload.get("role", "authenticated")
    
    # Extract timestamps
    exp = payload.get("exp")
    iat = payload.get("iat")
    
    return UserContext(
        user_id=user_id,
        email=email,
        role=role,
        token_exp=datetime.fromtimestamp(exp) if exp else None,
        token_iat=datetime.fromtimestamp(iat) if iat else None,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserContext:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: UserContext = Depends(get_current_user)):
            return {"user_id": user.user_id}
    
    Args:
        credentials: HTTP Authorization header credentials.
    
    Returns:
        UserContext for the authenticated user.
    
    Raises:
        HTTPException: If authentication fails.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(credentials.credentials)
        user = extract_user_context(payload)
        logger.debug(f"Authenticated user: {user.user_id}")
        return user
    except AuthError as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserContext]:
    """
    FastAPI dependency to optionally get the current user.
    
    Returns None if no valid token provided (instead of raising an error).
    Useful for routes that work with or without authentication.
    
    Args:
        credentials: HTTP Authorization header credentials.
    
    Returns:
        UserContext if authenticated, None otherwise.
    """
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        return extract_user_context(payload)
    except AuthError:
        return None

