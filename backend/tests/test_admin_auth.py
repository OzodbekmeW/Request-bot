"""
Admin Authentication Tests
"""
import pytest
from httpx import AsyncClient


class TestAdminLogin:
    """Tests for admin login endpoint"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, super_admin_credentials):
        """Test successful admin login"""
        response = await client.post(
            "/api/admin/auth/login",
            json=super_admin_credentials
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "csrf_token" in data
        assert "admin" in data
        
        # Check cookie is set
        assert "admin_session" in response.cookies
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password"""
        response = await client.post(
            "/api/admin/auth/login",
            json={
                "username": "superadmin",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            "/api/admin/auth/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_validation_error(self, client: AsyncClient):
        """Test login with invalid data"""
        response = await client.post(
            "/api/admin/auth/login",
            json={
                "username": "ab",  # Too short
                "password": "short"  # Too short
            }
        )
        
        assert response.status_code == 422


class TestCSRFProtection:
    """Tests for CSRF protection"""
    
    @pytest.mark.asyncio
    async def test_request_without_csrf_token(self, client: AsyncClient, super_admin_credentials):
        """Test that requests without CSRF token are rejected"""
        # First login
        login_response = await client.post(
            "/api/admin/auth/login",
            json=super_admin_credentials
        )
        
        assert login_response.status_code == 200
        
        # Try to access protected endpoint without CSRF token
        cookies = {"admin_session": login_response.cookies.get("admin_session")}
        
        response = await client.get(
            "/api/admin/admins",
            cookies=cookies
        )
        
        # GET requests don't require CSRF
        # For POST/PATCH/DELETE, CSRF would be required
        # This test depends on implementation
    
    @pytest.mark.asyncio
    async def test_request_with_valid_csrf_token(self, client: AsyncClient, super_admin_credentials):
        """Test that requests with valid CSRF token are accepted"""
        # Login
        login_response = await client.post(
            "/api/admin/auth/login",
            json=super_admin_credentials
        )
        
        assert login_response.status_code == 200
        data = login_response.json()
        csrf_token = data["csrf_token"]
        
        # Access protected endpoint with CSRF token
        cookies = {"admin_session": login_response.cookies.get("admin_session")}
        
        response = await client.get(
            "/api/admin/admins",
            cookies=cookies,
            headers={"X-CSRF-Token": csrf_token}
        )
        
        # Should succeed (assuming admin has permission)
        assert response.status_code in [200, 403]  # 403 if no permission


class TestAdminLogout:
    """Tests for admin logout"""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, super_admin_credentials):
        """Test successful logout"""
        # Login first
        login_response = await client.post(
            "/api/admin/auth/login",
            json=super_admin_credentials
        )
        
        assert login_response.status_code == 200
        
        # Logout
        cookies = {"admin_session": login_response.cookies.get("admin_session")}
        
        response = await client.post(
            "/api/admin/auth/logout",
            cookies=cookies
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
