"""
AK MCP Client.

Client for calling the AK (AlphaKernel) MCP tool.
AK is the primary reasoning engine that routes to other tools including Hyperion.
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Optional

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

# AK MCP endpoint
AK_MCP_URL = "https://n8n-dev-u36296.vm.elestio.app/mcp/4be5610b-62a1-45d8-b4d4-1080d1a88762"


class AKError(Exception):
    """Base exception for AK MCP errors."""
    
    def __init__(self, message: str, code: str = "ak_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AKSessionError(AKError):
    """Session initialization failed."""
    pass


class AKToolError(AKError):
    """Tool call failed."""
    pass


class AKClient:
    """
    Client for AK MCP interactions.
    
    Creates a new session per instance (one client per request pattern).
    """
    
    def __init__(self, timeout: float = 300.0):
        """
        Initialize AK client.
        
        Args:
            timeout: Request timeout in seconds (default 5 minutes for long operations)
        """
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.chat_session_id: str = str(uuid.uuid4())
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "AKClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        await self._initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _initialize_session(self) -> None:
        """
        Initialize MCP session with AK.
        
        Raises:
            AKSessionError: If session initialization fails.
        """
        if not self._client:
            raise AKSessionError("Client not initialized. Use async context manager.")
        
        try:
            response = await self._client.post(
                AK_MCP_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": "init",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "academic-research-tool",
                            "version": "1.0"
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            # Extract session ID from response header
            self.session_id = response.headers.get("mcp-session-id")
            
            if not self.session_id:
                # Try to parse from response body or use a generated one
                logger.warning("No mcp-session-id in response headers, generating one")
                self.session_id = str(uuid.uuid4())
            
            logger.info(f"AK session initialized: {self.session_id[:8]}...")
            
        except httpx.HTTPError as e:
            raise AKSessionError(f"Failed to initialize AK session: {e}")
    
    async def call(self, query: str) -> str:
        """
        Call AK with a natural language query.
        
        Args:
            query: Natural language instruction for AK.
        
        Returns:
            AK's response as a string.
        
        Raises:
            AKToolError: If the call fails.
        """
        if not self._client or not self.session_id:
            raise AKToolError("Client not initialized. Use async context manager.")
        
        try:
            response = await self._client.post(
                AK_MCP_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": f"ak_{uuid.uuid4().hex[:8]}",
                    "method": "tools/call",
                    "params": {
                        "name": "AK",
                        "arguments": {
                            "query": query,
                            "sessionId": self.chat_session_id
                        }
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": self.session_id
                }
            )
            
            # Parse SSE response
            return self._parse_sse_response(response.text)
            
        except httpx.HTTPError as e:
            raise AKToolError(f"AK call failed: {e}")
    
    def _parse_sse_response(self, response_text: str) -> str:
        """
        Parse SSE (Server-Sent Events) response from AK.
        
        Args:
            response_text: Raw SSE response text.
        
        Returns:
            Extracted response content.
        """
        # SSE format: lines starting with "data: " contain JSON
        output_parts = []
        
        for line in response_text.split("\n"):
            line = line.strip()
            
            if line.startswith("data:"):
                data_str = line[5:].strip()
                
                if not data_str or data_str == "[DONE]":
                    continue
                
                try:
                    data = json.loads(data_str)
                    
                    # Extract result from JSON-RPC response
                    if "result" in data:
                        result = data["result"]
                        
                        # Handle different result formats
                        if isinstance(result, dict):
                            if "content" in result:
                                # Standard tool response
                                for content_item in result.get("content", []):
                                    if content_item.get("type") == "text":
                                        output_parts.append(content_item.get("text", ""))
                            elif "output" in result:
                                output_parts.append(result["output"])
                        elif isinstance(result, list):
                            # Array of results
                            for item in result:
                                if isinstance(item, dict) and "output" in item:
                                    output_parts.append(item["output"])
                        elif isinstance(result, str):
                            output_parts.append(result)
                            
                except json.JSONDecodeError:
                    # Not JSON, might be partial data
                    continue
        
        if not output_parts:
            # Fallback: try to extract any text content
            logger.warning("No structured output found in SSE response")
            return response_text
        
        return "\n".join(output_parts)


async def call_ak(query: str, timeout: float = 300.0) -> str:
    """
    Convenience function to call AK with a single query.
    
    Creates a new client/session for each call.
    
    Args:
        query: Natural language query for AK.
        timeout: Request timeout in seconds.
    
    Returns:
        AK's response.
    """
    async with AKClient(timeout=timeout) as client:
        return await client.call(query)

