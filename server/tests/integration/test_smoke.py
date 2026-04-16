"""
自动化冒烟测试 - 验证系统核心服务是否正常启动和运行
"""
import pytest
from httpx import AsyncClient


class TestSmokeTest:
    """系统冒烟测试 - 验证基础服务和核心功能"""
    
    @pytest.mark.asyncio
    async def test_app_startup(self, async_client: AsyncClient):
        """测试应用启动和健康检查"""
        # 1. 根路径可访问
        response = await async_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """测试健康检查接口"""
        response = await async_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_database_connection(self, async_client: AsyncClient):
        """测试数据库连接和读写"""
        # 通过查询建筑列表验证数据库连接
        response = await async_client.get("/api/query/buildings")
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "data" in data
        # 应该能获取到建筑列表（即使为空也是正常）
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_core_api_endpoints_exist(self, async_client: AsyncClient):
        """测试核心API端点是否存在"""
        core_endpoints = [
            "/api/query/buildings",
            "/api/query/meters",
            "/api/statistics/summary",
            "/api/charts/trend",
            "/api/auth/login",
        ]
        
        for endpoint in core_endpoints:
            response = await async_client.get(endpoint)
            # 端点应该存在（返回200、400、422都可以，但不能是404）
            assert response.status_code != 404, f"端点 {endpoint} 不存在"
    
    @pytest.mark.asyncio
    async def test_user_authentication_flow(self, async_client: AsyncClient):
        """测试用户登录认证流程"""
        # 尝试使用测试账号登录
        login_data = {
            "account": "13800138000",
            "password": "123456",
            "login_type": "auto"
        }
        
        response = await async_client.post("/api/auth/login", json=login_data)
        
        # 登录接口应该存在并返回响应（成功或失败都可以）
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # 如果登录成功，应该返回token或用户信息
            assert "code" in data or "token" in data or "user" in data
    
    @pytest.mark.asyncio
    async def test_data_query_capability(self, async_client: AsyncClient):
        """测试数据查询能力"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-07"
        }
        
        response = await async_client.get("/api/query/raw", params=params)
        
        # 查询接口应该正常工作
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "data" in data
    
    @pytest.mark.asyncio
    async def test_statistics_calculation(self, async_client: AsyncClient):
        """测试统计计算功能"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        # 测试汇总统计
        response = await async_client.get("/api/statistics/summary", params=params)
        assert response.status_code != 404
        
        # 测试COP计算
        response = await async_client.get("/api/statistics/cop", params=params)
        assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_chart_data_generation(self, async_client: AsyncClient):
        """测试图表数据生成"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "metric": "electricity",
            "start_date": "2016-07-01",
            "end_date": "2016-07-07"
        }
        
        response = await async_client.get("/api/charts/trend", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # 图表数据应该是数组或对象
            assert isinstance(data, (list, dict))
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_service(self, async_client: AsyncClient):
        """测试异常检测服务"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/anomaly", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # 异常检测结果应该是列表或包含异常信息的对象
            assert isinstance(data, (list, dict))
    
    @pytest.mark.asyncio
    async def test_error_handling(self, async_client: AsyncClient):
        """测试错误处理机制"""
        # 访问不存在的端点
        response = await async_client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        # 使用无效参数调用接口
        response = await async_client.get("/api/query/raw", params={"invalid": "param"})
        # 应该返回适当的错误响应（200 with error code, 400, 或 422）
        assert response.status_code in [200, 400, 422]


class TestSmokeTestDataIntegrity:
    """冒烟测试 - 数据完整性验证"""
    
    @pytest.mark.asyncio
    async def test_buildings_data_exists(self, async_client: AsyncClient):
        """验证建筑数据存在"""
        response = await async_client.get("/api/query/buildings")
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该有建筑数据
        assert len(data["data"]) > 0, "数据库中应该存在建筑数据"
    
    @pytest.mark.asyncio
    async def test_meters_data_exists(self, async_client: AsyncClient):
        """验证监测点数据存在"""
        response = await async_client.get("/api/query/meters")
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该有监测点数据
        assert len(data["data"]) > 0, "数据库中应该存在监测点数据"
    
    @pytest.mark.asyncio
    async def test_energy_data_exists(self, async_client: AsyncClient):
        """验证能耗数据存在"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31",
            "limit": 1
        }
        
        response = await async_client.get("/api/query/raw", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该有能耗数据
        assert len(data["data"]) > 0, "数据库中应该存在能耗数据"
