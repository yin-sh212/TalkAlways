# test_db_connection.py
import asyncio
import aiomysql
from app.config import config


async def test_connection():
    print(f"🔌 尝试连接数据库...")
    print(f"Host: {config.DB_HOST}")
    print(f"Port: {config.DB_PORT}")
    print(f"User: {config.DB_USER}")
    print(f"Database: {config.DB_NAME}")

    try:
        pool = await aiomysql.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_NAME,
            minsize=1,
            maxsize=1
        )

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
                print(f"✅ 数据库连接成功！结果: {result}")

        pool.close()
        await pool.wait_closed()
        return True

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_connection())