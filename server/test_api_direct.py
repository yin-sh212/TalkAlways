# test_api_direct.py
import asyncio
import httpx
import json


async def test_chat_api():
    url = "http://localhost:8000/api/chat/ask"

    # 测试问题
    test_queries = [
        "B001建筑昨天用电量多少？",
        "冷水机组故障怎么处理",
        "你好"
    ]

    async with httpx.AsyncClient() as client:
        for query in test_queries:
            print(f"\n🔍 测试问题: {query}")
            try:
                response = await client.post(
                    url,
                    json={"query": query, "building_id": "B001"},
                    timeout=30.0
                )
                print(f"状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"回答: {data.get('answer', '无回答')[:100]}...")
                else:
                    print(f"错误: {response.text}")
            except Exception as e:
                print(f"异常: {e}")


if __name__ == "__main__":
    asyncio.run(test_chat_api())