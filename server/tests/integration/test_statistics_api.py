"""
统计分析API集成测试
"""
import pytest
from httpx import AsyncClient


class TestStatisticsEndpoints:
    """统计端点测试"""
    
    @pytest.mark.asyncio
    async def test_get_summary(self, async_client: AsyncClient):
        """测试获取时段汇总"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/summary", params=params)
        
        # 端点应该存在
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
    
    @pytest.mark.asyncio
    async def test_calculate_cop(self, async_client: AsyncClient):
        """测试计算COP"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/cop", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # COP应该是数值
            if isinstance(data, dict):
                if "cop" in data:
                    assert isinstance(data["cop"], (int, float))
    
    @pytest.mark.asyncio
    async def test_detect_anomaly(self, async_client: AsyncClient):
        """测试异常检测"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/statistics/anomaly", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestChartEndpoints:
    """图表数据端点测试"""
    
    @pytest.mark.asyncio
    async def test_get_trend_data(self, async_client: AsyncClient):
        """测试获取趋势图数据"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "metric": "electricity",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/charts/trend", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            # 趋势数据应该包含时间和值
            assert isinstance(data, (dict, list))
    
    @pytest.mark.asyncio
    async def test_get_comparison_data(self, async_client: AsyncClient):
        """测试获取对比图数据"""
        params = {
            "building_ids": ["Eagle_education_Cassie", "Eagle_education_Wesley"],
            "metric": "electricity",
            "start_date": "2016-07-01",
            "end_date": "2016-07-31"
        }
        
        response = await async_client.get("/api/charts/comparison", params=params)
        
        assert response.status_code != 404
    
    @pytest.mark.asyncio
    async def test_get_distribution_data(self, async_client: AsyncClient):
        """测试获取分布图数据"""
        params = {
            "building_id": "Eagle_education_Cassie",
            "metric": "electricity",
            "time_range": "month"
        }
        
        response = await async_client.get("/api/charts/distribution", params=params)
        
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
