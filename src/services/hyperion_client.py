"""
Hyperion RAG Client.

Client for Hyperion/LightRAG operations via AK MCP.
Uses AK as the routing layer to access Hyperion tools.
"""

import json
import logging
import re
from typing import Optional

import httpx

from src.config import get_settings
from src.models.hyperion import (
    DeleteResult,
    DocumentStatus,
    HyperionDocument,
    HyperionDocumentList,
    IngestRequest,
    IngestResult,
    PipelineStatus,
    QueryResult,
    ChunkReference,
    UploadResult,
)
from src.services.ak_client import AKClient, AKError, call_ak

logger = logging.getLogger(__name__)


# LightRAG direct API configuration loaded from settings


class HyperionError(Exception):
    """Base exception for Hyperion operations."""
    
    def __init__(self, message: str, operation: str = "unknown"):
        self.message = message
        self.operation = operation
        super().__init__(self.message)


class HyperionClient:
    """
    Client for Hyperion RAG operations.
    
    Wraps AK MCP calls with Hyperion-specific instructions.
    Creates one client per request (no session sharing).
    
    Usage:
        async with HyperionClient() as client:
            docs = await client.list_documents()
            result = await client.query("What methods were used?")
    """
    
    def __init__(self, timeout: float = 300.0):
        """
        Initialize Hyperion client.
        
        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self._ak_client: Optional[AKClient] = None
    
    async def __aenter__(self) -> "HyperionClient":
        """Async context manager entry."""
        self._ak_client = AKClient(timeout=self.timeout)
        await self._ak_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._ak_client:
            await self._ak_client.__aexit__(exc_type, exc_val, exc_tb)
            self._ak_client = None
    
    async def _call_ak(self, prompt: str) -> str:
        """
        Call AK with a Hyperion-related prompt.
        
        Args:
            prompt: Instruction for AK.
        
        Returns:
            AK's response.
        
        Raises:
            HyperionError: If the call fails.
        """
        if not self._ak_client:
            raise HyperionError("Client not initialized. Use async context manager.", "call")
        
        try:
            return await self._ak_client.call(prompt)
        except AKError as e:
            raise HyperionError(f"AK call failed: {e.message}", "call")
    
    async def list_documents(self) -> HyperionDocumentList:
        """
        List all documents in Hyperion.
        
        Returns:
            HyperionDocumentList with all stored documents.
        """
        prompt = """List all documents currently stored in the Hyperion RAG knowledge base. 
        Use the RAG tool's get_list_of_all_docs function.
        Return the complete list with document names and their status (processed/failed)."""
        
        try:
            response = await self._call_ak(prompt)
            
            # Parse the response to extract document info
            documents = []
            failed_count = 0
            
            # Look for document names in the response
            # AK typically returns a formatted list
            lines = response.split("\n")
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and headers
                if not line or line.startswith("#") or line.startswith("---"):
                    continue
                
                # Check for failed documents
                if "failed" in line.lower():
                    failed_count += 1
                    # Extract name if possible
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        documents.append(HyperionDocument(
                            name=match.group(1),
                            status=DocumentStatus.FAILED
                        ))
                    continue
                
                # Look for numbered list items or quoted names
                match = re.search(r'(?:\d+\.\s*)?["\']?([^"\']+(?:\.[a-z]+)?)["\']?', line)
                if match:
                    name = match.group(1).strip()
                    # Filter out common non-document strings
                    if name and len(name) > 2 and not name.startswith("###"):
                        documents.append(HyperionDocument(
                            name=name,
                            status=DocumentStatus.PROCESSED
                        ))
            
            return HyperionDocumentList(
                documents=documents,
                total_count=len(documents),
                failed_count=failed_count
            )
            
        except Exception as e:
            logger.exception(f"Error listing documents: {e}")
            raise HyperionError(f"Failed to list documents: {e}", "list")
    
    async def query(self, query: str, format: Optional[str] = None) -> QueryResult:
        """
        Query the Hyperion knowledge base.
        
        Args:
            query: Natural language query.
            format: Optional format specification for the response.
        
        Returns:
            QueryResult with response and source references.
        """
        format_instruction = f" Format the response as: {format}" if format else ""
        
        prompt = f"""Query the Hyperion RAG knowledge base with this question:

Question: {query}
{format_instruction}

Use the RAG tool's query_knowledge function. Include source attribution in your response."""
        
        try:
            response = await self._call_ak(prompt)
            
            # Extract source references from the response
            sources = self._extract_sources(response)
            
            return QueryResult(
                success=True,
                query=query,
                response=response,
                sources=sources
            )
            
        except Exception as e:
            logger.exception(f"Error querying Hyperion: {e}")
            return QueryResult(
                success=False,
                query=query,
                response="",
                error=str(e)
            )
    
    def _extract_sources(self, response: str) -> list[ChunkReference]:
        """
        Extract source references from AK's response.
        
        Args:
            response: AK's response text.
        
        Returns:
            List of ChunkReference objects.
        """
        sources = []
        
        # Look for common source citation patterns
        # Pattern 1: "from document_name" or "in document_name"
        doc_pattern = r'(?:from|in|source:|according to)\s+["\']?([^"\'.,\n]+)["\']?'
        matches = re.findall(doc_pattern, response, re.IGNORECASE)
        
        for match in matches:
            name = match.strip()
            if name and len(name) > 2:
                sources.append(ChunkReference(doc_name=name))
        
        # Deduplicate
        seen = set()
        unique_sources = []
        for source in sources:
            if source.doc_name not in seen:
                seen.add(source.doc_name)
                unique_sources.append(source)
        
        return unique_sources
    
    async def ingest(self, texts: list[str], doc_name: str) -> IngestResult:
        """
        Ingest text chunks into Hyperion.
        
        Args:
            texts: List of text chunks to ingest.
            doc_name: Document name for all chunks.
        
        Returns:
            IngestResult with status and track ID.
        """
        # Format the texts array for AK
        texts_json = json.dumps(texts)
        doc_names_json = json.dumps([doc_name] * len(texts))
        
        prompt = f"""Use the Hyperion RAG tool to ingest the following text chunks. 
Use the ingest_multiple_knowledge tool with:
- texts: {texts_json}
- documentName: {doc_names_json}

Report the result including any track ID or confirmation."""
        
        try:
            response = await self._call_ak(prompt)
            
            # Check for success indicators
            success = any(word in response.lower() for word in [
                "success", "ingested", "processed", "track id", "completed"
            ])
            
            # Try to extract track ID
            track_id = None
            track_match = re.search(r'track[_\s]?id[:\s]+([a-zA-Z0-9_-]+)', response, re.IGNORECASE)
            if track_match:
                track_id = track_match.group(1)
            
            # Check for errors
            error = None
            if not success:
                if "error" in response.lower() or "failed" in response.lower():
                    error = response
            
            return IngestResult(
                success=success,
                doc_name=doc_name,
                chunk_count=len(texts),
                track_id=track_id,
                error=error
            )
            
        except Exception as e:
            logger.exception(f"Error ingesting to Hyperion: {e}")
            return IngestResult(
                success=False,
                doc_name=doc_name,
                chunk_count=len(texts),
                error=str(e)
            )
    
    async def delete(self, doc_name: str) -> DeleteResult:
        """
        Delete a document from Hyperion.
        
        Args:
            doc_name: Name of the document to delete.
        
        Returns:
            DeleteResult with status.
        """
        prompt = f"""Delete the document named "{doc_name}" from the Hyperion RAG knowledge base.
Use the RAG tool's delete_knowledge function with target: "{doc_name}".
Confirm the deletion."""
        
        try:
            response = await self._call_ak(prompt)
            
            # Check for success
            success = any(word in response.lower() for word in [
                "deleted", "removed", "success", "completed"
            ])
            
            # Check for errors
            error = None
            if not success:
                if "error" in response.lower() or "failed" in response.lower():
                    error = response
            
            return DeleteResult(
                success=success,
                doc_name=doc_name,
                deleted_count=1 if success else 0,
                error=error
            )
            
        except Exception as e:
            logger.exception(f"Error deleting from Hyperion: {e}")
            return DeleteResult(
                success=False,
                doc_name=doc_name,
                error=str(e)
            )
    
    async def upload_pdf(self, file_bytes: bytes, filename: str) -> UploadResult:
        """
        Upload a PDF file directly to LightRAG.
        
        Uses LightRAG's /documents/upload endpoint directly (not via AK)
        for reliable binary file handling.
        
        Args:
            file_bytes: PDF file content as bytes.
            filename: Name for the uploaded file.
        
        Returns:
            UploadResult with doc_id and track_id.
        """
        settings = get_settings()
        
        if not settings.lightrag_api_key:
            return UploadResult(
                success=False,
                filename=filename,
                status="failed",
                error="LightRAG API key not configured. Set LIGHTRAG_API_KEY in environment.",
            )
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Prepare multipart form data
                files = {
                    "file": (filename, file_bytes, "application/pdf")
                }
                
                response = await client.post(
                    f"{settings.lightrag_url}/documents/upload",
                    headers={
                        "X-API-Key": settings.lightrag_api_key
                    },
                    files=files,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # LightRAG returns status and potentially a track_id
                    status = data.get("status", "unknown")
                    
                    return UploadResult(
                        success=status in ["success", "duplicated", "processing"],
                        filename=filename,
                        doc_id=data.get("id"),
                        track_id=data.get("track_id"),
                        status=status,
                        error=data.get("message") if status == "error" else None,
                    )
                else:
                    error_text = response.text
                    logger.error(f"LightRAG upload failed: {response.status_code} - {error_text}")
                    return UploadResult(
                        success=False,
                        filename=filename,
                        status="failed",
                        error=f"HTTP {response.status_code}: {error_text}",
                    )
                    
        except Exception as e:
            logger.exception(f"Error uploading to LightRAG: {e}")
            return UploadResult(
                success=False,
                filename=filename,
                status="failed",
                error=str(e),
            )
    
    async def get_pipeline_status(self) -> PipelineStatus:
        """
        Get the current status of the LightRAG processing pipeline.
        
        Useful for checking if uploads are still being processed.
        
        Returns:
            PipelineStatus with current processing state.
        """
        settings = get_settings()
        
        if not settings.lightrag_api_key:
            logger.warning("LightRAG API key not configured, cannot check pipeline status")
            return PipelineStatus()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.lightrag_url}/documents/pipeline_status",
                    headers={
                        "X-API-Key": settings.lightrag_api_key
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return PipelineStatus(
                        busy=data.get("busy", False),
                        job_name=data.get("job_name"),
                        job_start=data.get("job_start"),
                        docs_count=data.get("docs", 0),
                        batches=data.get("batchs", 0),
                        current_batch=data.get("cur_batch", 0),
                        latest_message=data.get("latest_message"),
                        autoscanned=data.get("autoscanned", False),
                        request_pending=data.get("request_pending", False),
                    )
                else:
                    logger.warning(f"Pipeline status check failed: {response.status_code}")
                    return PipelineStatus()
                    
        except Exception as e:
            logger.exception(f"Error getting pipeline status: {e}")
            return PipelineStatus()


# Convenience functions for one-off operations

async def hyperion_list_documents() -> HyperionDocumentList:
    """List all documents in Hyperion (convenience function)."""
    async with HyperionClient() as client:
        return await client.list_documents()


async def hyperion_query(query: str, format: Optional[str] = None) -> QueryResult:
    """Query Hyperion (convenience function)."""
    async with HyperionClient() as client:
        return await client.query(query, format)


async def hyperion_ingest(texts: list[str], doc_name: str) -> IngestResult:
    """Ingest chunks to Hyperion (convenience function)."""
    async with HyperionClient() as client:
        return await client.ingest(texts, doc_name)


async def hyperion_delete(doc_name: str) -> DeleteResult:
    """Delete document from Hyperion (convenience function)."""
    async with HyperionClient() as client:
        return await client.delete(doc_name)


async def hyperion_upload_pdf(file_bytes: bytes, filename: str) -> UploadResult:
    """Upload PDF to LightRAG (convenience function)."""
    async with HyperionClient() as client:
        return await client.upload_pdf(file_bytes, filename)


async def hyperion_pipeline_status() -> PipelineStatus:
    """Get LightRAG pipeline status (convenience function)."""
    async with HyperionClient() as client:
        return await client.get_pipeline_status()

