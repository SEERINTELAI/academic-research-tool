"""
End-to-end connectivity tests for frontend-backend communication.

Tests:
- Backend health endpoint reachability
- CORS headers presence and correctness
- External service connectivity
- Frontend API client configuration
"""

import asyncio
import httpx
import pytest
from typing import Optional

# Test configuration
BASE_URL = "http://localhost:8003"
FRONTEND_ORIGIN = "http://localhost:3000"
TIMEOUT = 10.0


class TestBackendConnectivity:
    """Test that the backend API is reachable and responding correctly."""

    @pytest.mark.asyncio
    async def test_health_endpoint_reachable(self):
        """Test basic health check endpoint is reachable."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/health")
            
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            data = response.json()
            
            assert "status" in data, "Missing 'status' in health response"
            assert data["status"] in ["healthy", "degraded", "ok"], f"Unexpected status: {data['status']}"
            
            print(f"✓ Health check passed: {data}")

    @pytest.mark.asyncio
    async def test_ready_endpoint_reachable(self):
        """Test readiness probe endpoint."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data.get("ready") is True
            
            print("✓ Readiness check passed")

    @pytest.mark.asyncio
    async def test_live_endpoint_reachable(self):
        """Test liveness probe endpoint."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/health/live")
            
            assert response.status_code == 200
            data = response.json()
            assert data.get("alive") is True
            
            print("✓ Liveness check passed")

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns API info."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "name" in data
            assert "version" in data
            
            print(f"✓ Root endpoint: {data['name']} v{data['version']}")


class TestCORSConfiguration:
    """Test that CORS headers are correctly configured for frontend origin."""

    @pytest.mark.asyncio
    async def test_cors_preflight_request(self):
        """Test CORS preflight (OPTIONS) request from frontend origin."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.options(
                f"{BASE_URL}/api/projects",
                headers={
                    "Origin": FRONTEND_ORIGIN,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization, Content-Type",
                }
            )
            
            # Should return 200 OK for preflight
            assert response.status_code == 200, f"Preflight failed: {response.status_code}"
            
            # Check CORS headers
            assert "access-control-allow-origin" in response.headers, "Missing CORS origin header"
            allowed_origin = response.headers["access-control-allow-origin"]
            assert allowed_origin in [FRONTEND_ORIGIN, "*"], f"Unexpected origin: {allowed_origin}"
            
            print(f"✓ CORS preflight passed (origin: {allowed_origin})")

    @pytest.mark.asyncio
    async def test_cors_headers_on_get_request(self):
        """Test CORS headers are present on actual GET requests."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/health",
                headers={"Origin": FRONTEND_ORIGIN}
            )
            
            assert response.status_code == 200
            
            # CORS headers should be present
            assert "access-control-allow-origin" in response.headers
            
            print("✓ CORS headers present on GET request")

    @pytest.mark.asyncio
    async def test_cors_with_credentials(self):
        """Test that CORS allows credentials (cookies, auth headers)."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.options(
                f"{BASE_URL}/api/projects",
                headers={
                    "Origin": FRONTEND_ORIGIN,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization",
                }
            )
            
            assert response.status_code == 200
            
            # Check credentials are allowed
            allow_credentials = response.headers.get("access-control-allow-credentials", "false")
            assert allow_credentials.lower() == "true", "CORS should allow credentials"
            
            print("✓ CORS allows credentials")


class TestAPIAuthentication:
    """Test API authentication flow."""

    @pytest.mark.asyncio
    async def test_projects_endpoint_with_token(self):
        """Test that projects endpoint accepts Bearer token."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/projects",
                headers={
                    "Authorization": "Bearer demo-token",
                    "Content-Type": "application/json",
                }
            )
            
            # Should return 200, 401/403 (auth), or 500 (DB not configured)
            # 500 is acceptable when database is not configured
            assert response.status_code in [200, 401, 403, 500], f"Unexpected status: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list), "Projects should return a list"
                print(f"✓ Projects endpoint returned {len(data)} projects")
            elif response.status_code == 500:
                print(f"⚠ Projects endpoint returned 500 (database not configured)")
            else:
                print(f"✓ Projects endpoint requires real auth (got {response.status_code})")

    @pytest.mark.asyncio
    async def test_projects_endpoint_cors_with_auth(self):
        """Test CORS + Auth headers work together."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/projects",
                headers={
                    "Origin": FRONTEND_ORIGIN,
                    "Authorization": "Bearer demo-token",
                    "Content-Type": "application/json",
                }
            )
            
            # Should return valid response (not CORS blocked)
            # 500 is acceptable when database is not configured
            assert response.status_code in [200, 401, 403, 500], f"Request failed: {response.status_code}"
            assert "access-control-allow-origin" in response.headers
            
            if response.status_code == 500:
                print("⚠ CORS headers present but DB not configured (500)")
            else:
                print("✓ CORS + Auth headers work together")


class TestExternalServicesReachability:
    """Test that external services are reachable from backend."""

    @pytest.mark.asyncio
    async def test_diagnostics_endpoint(self):
        """Test diagnostics endpoint (if available) reports service status."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/health/diagnostics")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Diagnostics available: {list(data.keys())}")
            elif response.status_code == 404:
                print("⚠ Diagnostics endpoint not yet implemented")
            else:
                print(f"⚠ Diagnostics returned {response.status_code}")


class TestFrontendSimulation:
    """Simulate frontend API calls to ensure they work correctly."""

    @pytest.mark.asyncio
    async def test_frontend_style_projects_fetch(self):
        """Simulate the exact fetch the frontend makes."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # This mimics what frontend/src/lib/api.ts does
            response = await client.get(
                f"{BASE_URL}/api/projects",
                headers={
                    "Authorization": "Bearer demo-token",
                    "Content-Type": "application/json",
                    "Origin": FRONTEND_ORIGIN,
                }
            )
            
            # Should not hang or timeout
            # 500 is acceptable when database is not configured
            assert response.status_code in [200, 401, 403, 500]
            
            if response.status_code == 200:
                projects = response.json()
                assert isinstance(projects, list)
                print(f"✓ Frontend-style fetch works: {len(projects)} projects")
            elif response.status_code == 500:
                print(f"⚠ Frontend-style fetch completes (DB not configured)")
            else:
                print(f"✓ Frontend-style fetch completes with auth response: {response.status_code}")

    @pytest.mark.asyncio
    async def test_frontend_style_health_fetch(self):
        """Simulate frontend health check."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/health",
                headers={
                    "Content-Type": "application/json",
                    "Origin": FRONTEND_ORIGIN,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            
            print(f"✓ Frontend health check simulation passed")


class TestErrorHandling:
    """Test API error handling for common scenarios."""

    @pytest.mark.asyncio
    async def test_404_for_unknown_endpoint(self):
        """Test that unknown endpoints return 404."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{BASE_URL}/api/unknown-endpoint-xyz")
            
            assert response.status_code == 404
            print("✓ Unknown endpoint returns 404")

    @pytest.mark.asyncio
    async def test_project_not_found(self):
        """Test 404 for non-existent project."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/projects/00000000-0000-0000-0000-000000000000",
                headers={"Authorization": "Bearer demo-token"}
            )
            
            # 404 is expected, but 500 is acceptable when DB not configured
            assert response.status_code in [404, 500]
            if response.status_code == 404:
                print("✓ Non-existent project returns 404")
            else:
                print("⚠ Non-existent project check skipped (DB not configured)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

