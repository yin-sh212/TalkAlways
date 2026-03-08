# test_performance.py
import asyncio
import time
import aiohttp
from statistics import mean, median

BASE_URL = "http://localhost:8000"


async def test_api(session, name, url, method="GET", data=None):
    """测试单个API响应时间"""
    start = time.time()
    try:
        if method == "GET":
            async with session.get(url) as resp:
                await resp.json()
        else:
            async with session.post(url, json=data) as resp:
                await resp.json()
        elapsed = (time.time() - start) * 1000  # 毫秒
        print(f"✅ {name}: {elapsed:.1f}ms")
        return elapsed
    except Exception as e:
        print(f"❌ {name}: 失败 - {e}")
        return None


async def run_tests():
    """运行所有性能测试"""
    test_cases = [
        ("查询建筑列表", "GET", f"{BASE_URL}/api/query/buildings", None),
        ("查询5条数据", "GET", f"{BASE_URL}/api/query/raw?limit=5", None),
        ("查询100条数据", "GET", f"{BASE_URL}/api/query/raw?limit=100", None),
        ("周汇总", "GET",
         f"{BASE_URL}/api/statistics/summary?building_id=B001&start_date=2025-01-01&end_date=2025-01-31", None),
        ("异常检测", "GET",
         f"{BASE_URL}/api/statistics/anomaly?building_id=B001&start_date=2025-01-01&end_date=2025-01-31", None),
        ("趋势图", "GET", f"{BASE_URL}/api/charts/trend?building_id=B001&days=7", None),
        ("智能问答", "POST", f"{BASE_URL}/api/chat/ask", {"query": "B001昨天用电量", "building_id": "B001"}),
    ]

    results = []
    async with aiohttp.ClientSession() as session:
        for name, method, url, data in test_cases:
            elapsed = await test_api(session, name, url, method, data)
            if elapsed:
                results.append(elapsed)
            await asyncio.sleep(0.5)  # 避免请求太快

    if results:
        print("\n" + "=" * 50)
        print(f"📊 性能测试结果")
        print(f"平均响应时间: {mean(results):.1f}ms")
        print(f"中位数响应时间: {median(results):.1f}ms")
        print(f"最慢响应: {max(results):.1f}ms")
        print(f"最快响应: {min(results):.1f}ms")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_tests())