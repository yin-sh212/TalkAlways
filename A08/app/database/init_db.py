import asyncio
import aiomysql
from app.config import config
from app.database.model import CREATE_TABLES_SQL
from app.services.data_generator import generate_all_data


async def init_database():
    """初始化数据库：创建库、建表、导入测试数据"""
    # 先连接MySQL（不指定数据库）
    pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset='utf8mb4'
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 创建数据库（如果不存在）
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME} CHARACTER SET utf8mb4")
            print(f"✅ 数据库 {config.DB_NAME} 创建成功或已存在")

            # 使用数据库
            await cursor.execute(f"USE {config.DB_NAME}")

            # 执行建表语句
            for sql in CREATE_TABLES_SQL.split(';'):
                if sql.strip():
                    await cursor.execute(sql)
            print("✅ 数据表创建成功")

    pool.close()
    await pool.wait_closed()

    # 连接具体数据库，插入测试数据
    db_pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        db=config.DB_NAME,
        charset='utf8mb4'
    )

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 调用数据生成器
            await generate_all_data(cursor)
            await conn.commit()
            print("✅ 测试数据生成完成")

    db_pool.close()
    await db_pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(init_database())
    print("🎉 数据库初始化完成！")