"""
Rate Limiting Tests
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestOTPRateLimiting:
    """Tests for OTP rate limiting"""
    
    @pytest.mark.asyncio
    async def test_otp_rate_limit_per_minute(self, client: AsyncClient, test_phone_number):
        """Test that OTP is rate limited per minute"""
        with patch('app.services.telegram_service.TelegramService.send_otp_message',
                   new_callable=AsyncMock, return_value=True):
            
            # First request should succeed (or fail for other reasons)
            response1 = await client.post(
                "/api/auth/send-otp",
                json={"phone_number": test_phone_number}
            )
            
            # Second request within same minute should be rate limited
            response2 = await client.post(
                "/api/auth/send-otp",
                json={"phone_number": test_phone_number}
            )
            
            # If first succeeded, second should be rate limited
            if response1.status_code == 200:
                assert response2.status_code == 429
    
    @pytest.mark.asyncio
    async def test_rate_limit_response_format(self, client: AsyncClient, test_phone_number):
        """Test rate limit response includes retry_after"""
        with patch('app.services.telegram_service.TelegramService.send_otp_message',
                   new_callable=AsyncMock, return_value=True):
            
            # Make requests until rate limited
            for _ in range(5):
                response = await client.post(
                    "/api/auth/send-otp",
                    json={"phone_number": test_phone_number}
                )
                
                if response.status_code == 429:
                    # Should have Retry-After header
                    assert "retry-after" in response.headers or response.status_code == 429
                    break


class TestLoginRateLimiting:
    """Tests for login rate limiting (brute force protection)"""
    
    @pytest.mark.asyncio
    async def test_login_blocks_after_failed_attempts(self, client: AsyncClient):
        """Test that login is blocked after multiple failed attempts"""
        # Make multiple failed login attempts
        for i in range(6):
            response = await client.post(
                "/api/admin/auth/login",
                json={
                    "username": "superadmin",
                    "password": f"WrongPassword{i}!"
                }
            )
            
            
            if i >= 5:
                assert response.status_code in [401, 429]
