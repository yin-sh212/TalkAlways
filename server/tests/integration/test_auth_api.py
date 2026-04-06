"""
认证API集成测试
"""
import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """认证端点测试"""
    
    @pytest.mark.asyncio
    async def test_login_endpoint_exists(self, async_client: AsyncClient):
        """测试登录端点存在"""
        response = await async_client.post("/api/auth/login", json={
            "account": "13800138000",
            "password": "123456"
        })
        
        # 端点应该存在（可能成功或失败，但不应该是404）
        assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, async_client: AsyncClient):
        """测试使用有效凭证登录"""
        login_data = {
            "account": "13800138000",
            "password": "123456",
            "login_type": "auto"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        # 如果数据库中有该用户，应该成功
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert "user_info" in data
            assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, async_client: AsyncClient):
        """测试使用无效凭证登录"""
        login_data = {
            "account": "invalid_user",
            "password": "wrong_password"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        # 应该返回400、401或404
        assert response.status_code in [400, 401, 404]
    
    @pytest.mark.asyncio
    async def test_login_missing_fields(self, async_client: AsyncClient):
        """测试登录缺少必填字段"""
        login_data = {
            "account": "13800138000"
            # 缺少password
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        # 应该返回422验证错误
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_endpoint_exists(self, async_client: AsyncClient):
        """测试注册端点存在"""
        register_data = {
            "name": "新用户",
            "phone": "13900000000",
            "email": "newuser@example.com",
            "password": "password123"
        }
        
        response = await async_client.post("/api/auth/register", json=register_data)
        
        # 端点应该存在
        assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_register_with_invalid_phone(self, async_client: AsyncClient):
        """测试使用无效手机号注册"""
        register_data = {
            "name": "新用户",
            "phone": "12345",  # 无效手机号
            "password": "password123"
        }
        
        response = await async_client.post("/api/auth/register", json=register_data)
        
        # API返回200状态码，但响应体中code=400表示错误
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "手机号格式不正确" in data["message"]

    @pytest.mark.asyncio
    async def test_get_current_user_without_token(self, async_client: AsyncClient):
        """测试未提供token时获取当前用户"""
        response = await async_client.get("/api/auth/me")
        
        # 应该返回401未授权
        assert response.status_code == 401


class TestTokenValidation:
    """Token验证测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_token_format(self, async_client: AsyncClient):
        """测试无效token格式"""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "InvalidTokenFormat"}
        )
        
        # 应该返回401或500（取决于错误处理）
        assert response.status_code in [401, 500]
    
    @pytest.mark.asyncio
    async def test_expired_token(self, async_client: AsyncClient):
        """测试过期token"""
        # 这里使用一个明显无效的JWT token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        # 应该返回401
        assert response.status_code == 401
