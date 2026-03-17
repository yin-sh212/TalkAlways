# test_cloud_connection.py
import asyncio
from app.database.db import Database
from dotenv import load_dotenv
import os

load_dotenv()

async def test_connection():
    print("🔌 测试云端数据库连接...")
    print(f"Host: {os.getenv('DB_HOST')}")
    print(f"Database: {os.getenv('DB_NAME')}")
    print(f"User: {os.getenv('DB_USER')}")
    print(f"SSL: {os.getenv('DB_SSL')}")
    
    try:
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT VERSION()")
                version = await cursor.fetchone()
                print(f"✅ 连接成功！数据库版本: {version[0]}")
                
                # 查看表数量
                await cursor.execute("SHOW TABLES")
                tables = await cursor.fetchall()
                print(f"📊 表数量: {len(tables)}")
                
                # 查看数据量
                await cursor.execute("SELECT COUNT(*) FROM energy_consumption_new")
                count = await cursor.fetchone()
                print(f"⚡ 能耗数据: {count[0]} 条")
                
    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())