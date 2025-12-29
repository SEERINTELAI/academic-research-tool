"""
Frontend logging endpoint.

Receives logs from the frontend and writes them to the backend logs
for debugging and diagnostics.
"""

import logging
from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger("frontend")

# Configure frontend logger to stand out
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "🌐 FRONTEND | %(levelname)s | %(message)s"
))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/logs", tags=["Logs"])


class FrontendLogEntry(BaseModel):
    """A log entry from the frontend."""
    
    level: Literal["debug", "info", "warn", "error"] = "info"
    source: str = Field(..., description="Component or module name")
    message: str = Field(..., description="Log message")
    data: Optional[dict] = Field(None, description="Additional data")
    error: Optional[str] = Field(None, description="Error stack trace")
    url: Optional[str] = Field(None, description="Current page URL")
    user_agent: Optional[str] = Field(None, description="Browser user agent")
    timestamp: Optional[str] = Field(None, description="Client-side timestamp")


class LogBatch(BaseModel):
    """Batch of log entries from frontend."""
    
    logs: list[FrontendLogEntry]


@router.post("", status_code=204)
async def receive_logs(batch: LogBatch):
    """
    Receive logs from the frontend.
    
    This endpoint allows the frontend to send logs to the backend
    where they can be viewed in server logs for debugging.
    """
    for entry in batch.logs:
        # Format the log message
        parts = [f"[{entry.source}]", entry.message]
        
        if entry.url:
            parts.append(f"@ {entry.url}")
        
        if entry.data:
            parts.append(f"| data: {entry.data}")
        
        message = " ".join(parts)
        
        # Log at appropriate level
        if entry.level == "debug":
            logger.debug(message)
        elif entry.level == "info":
            logger.info(message)
        elif entry.level == "warn":
            logger.warning(message)
        elif entry.level == "error":
            logger.error(message)
            if entry.error:
                logger.error(f"  Stack: {entry.error}")


@router.post("/error", status_code=204)
async def receive_error(
    source: str,
    message: str,
    stack: Optional[str] = None,
    url: Optional[str] = None,
):
    """Quick endpoint for single error reporting."""
    logger.error(f"[{source}] {message} @ {url or 'unknown'}")
    if stack:
        for line in stack.split("\n")[:10]:  # First 10 lines
            logger.error(f"  {line}")

