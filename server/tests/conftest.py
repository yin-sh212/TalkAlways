"""
全局测试配置和fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database.db import Database


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_app():
    """测试应用实例"""
    return app


@pytest.fixture(scope="session")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """异步HTTP客户端"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def client() -> TestClient:
    """同步HTTP客户端"""
    return TestClient(app)


@pytest.fixture
async def db_connection():
    """数据库连接fixture"""
    # 确保数据库可用
    try:
        result = await Database.fetch_one("SELECT 1 as test")
        assert result is not None
    except Exception as e:
        pytest.skip(f"数据库不可用: {e}")
    
    yield Database


# 测试数据fixtures
@pytest.fixture
def sample_building_data():
    """示例建筑数据 - 使用实际存在的建筑ID"""
    return {
        "id": "Eagle_education_Cassie",
        "name": "Eagle_education_Cassie",
        "type": "教学楼",
        "area": 5000.0
    }


@pytest.fixture
def sample_meter_data():
    """示例监测点数据"""
    return {
        "id": "Eagle_education_Cassie_machine",
        "building_id": "Eagle_education_Cassie",
        "type": "综合设备",
        "status": "normal"
    }


@pytest.fixture
def sample_energy_data():
    """示例能耗数据 - 使用实际时间范围"""
    return {
        "building_id": "Eagle_education_Cassie",
        "meter_id": "Eagle_education_Cassie_machine",
        "timestamp": "2016-07-15 12:00:00",
        "electricity": 100.5,
        "water": 50.2,
        "supply_temp": 45.0,
        "return_temp": 40.0,
        "ambient_temp": 25.0,
        "humidity": 60.0,
        "occupancy": 50.0,
        "is_anomaly": False
    }


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "name": "测试用户",
        "phone": "13800138000",
        "email": "test@example.com",
        "password": "123456"
    }


@pytest.fixture
def sample_login_credentials():
    """示例登录凭证"""
    return {
        "account": "13800138000",
        "password": "123456",
        "login_type": "auto"
    }
