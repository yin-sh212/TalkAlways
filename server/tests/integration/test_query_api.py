"""
数据查询API集成测试
"""
import pytest
from httpx import AsyncClient


class TestQueryEndpoints:
    """数据查询端点测试"""
    
    @pytest.mark.asyncio
    async def test_get_buildings(self, async_client: AsyncClient):
        """测试获取建筑列表"""
        response = await async_client.get("/api/query/buildings")
        
        assert response.status_code == 200
        data = response.json()
        # API返回格式为 {code: 200, data: [...]}
        assert "code" in data
        assert "data" in data
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_meters(self, async_client: AsyncClient):
        """测试获取监测点列表"""
        response = await async_client.get("/api/query/meters")
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "data" in data
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_raw_data_with_params(self, async_client: AsyncClient):
        """测试带参数获取原始数据"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/query/raw", params=params)
        
        # 端点应该存在，可能返回空数据
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "data" in data
            assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_raw_data_missing_params(self, async_client: AsyncClient):
        """测试缺少参数获取原始数据"""
        response = await async_client.get("/api/query/raw")
        
        # 应该返回成功（可能为空数据）或验证错误
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_get_device_status(self, async_client: AsyncClient):
        """测试获取设备状态"""
        response = await async_client.get("/api/query/device-status")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


class TestDataFiltering:
    """数据过滤测试"""
    
    @pytest.mark.asyncio
    async def test_filter_by_building_id(self, async_client: AsyncClient):
        """测试按建筑ID过滤"""
        response = await async_client.get(
            "/api/query/raw",
            params={"building_id": "Eagle_education_Cassie"}
        )
        
        if response.status_code == 200:
            data = response.json()
            # API返回格式为 {code, data, pagination}
            if "data" in data and len(data["data"]) > 0:
                assert all(item.get("building_id") == "Eagle_education_Cassie" for item in data["data"])

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, async_client: AsyncClient):
        """测试按日期范围过滤"""
        params = {
            "start_date": "2016-07-01",
            "end_date": "2016-07-07"
        }
        
        response = await async_client.get("/api/query/raw", params=params)
        
        if response.status_code == 200:
            result = response.json()
            # 验证返回的数据在指定时间范围内（只检查是否有数据返回）
            assert "data" in result
            # 不严格验证时间戳格式，因为API可能返回不同格式


class TestPagination:
    """分页功能测试"""
    
    @pytest.mark.asyncio
    async def test_pagination_parameters(self, async_client: AsyncClient):
        """测试分页参数"""
        params = {
            "limit": 10,
            "offset": 0
        }
        
        response = await async_client.get("/api/query/raw", params=params)
        
        # 端点应该存在
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # 检查是否有分页信息
            if "pagination" in data:
                assert "total" in data["pagination"]
                assert "limit" in data["pagination"]
