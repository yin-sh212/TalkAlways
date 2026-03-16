import asyncio
import aiomysql
from app.config import config
from app.database.model import CREATE_TABLES_SQL
from app.services.data_generator import generate_all_data
import os
import ssl
from pathlib import Path


async def init_database():
    """初始化数据库：创建库、建表、导入测试数据"""
    
    # 准备 SSL 配置
    ssl_ctx = None
    ssl_ca = os.getenv("SSL_CA")
    is_tidb_cloud = "tidbcloud.com" in config.DB_HOST.lower()
    
    if is_tidb_cloud or ssl_ca:
        try:
            # 如果是相对路径，转换为绝对路径
            if ssl_ca and not Path(ssl_ca).is_absolute():
                ssl_ca = str(Path(__file__).parent.parent.parent / ssl_ca)
            
            # 创建 SSL 上下文
            ssl_ctx = ssl.create_default_context(cafile=ssl_ca) if ssl_ca else ssl.create_default_context()
            
            if is_tidb_cloud:
                ssl_ctx.check_hostname = True
                ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            
            # 处理客户端证书
            ssl_cert = os.getenv("SSL_CERT")
            ssl_key = os.getenv("SSL_KEY")
            if ssl_cert and ssl_key:
                if not Path(ssl_cert).is_absolute():
                    ssl_cert = str(Path(__file__).parent.parent.parent / ssl_cert)
                if not Path(ssl_key).is_absolute():
                    ssl_key = str(Path(__file__).parent.parent.parent / ssl_key)
                ssl_ctx.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
            
        except Exception as e:
            if is_tidb_cloud:
                raise Exception(f"TiDB Cloud 必须配置 SSL 证书：{e}")
    
    # 先连接 MySQL（不指定数据库）
    pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset='utf8mb4',
        ssl=ssl_ctx if ssl_ctx else None
    )

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 创建数据库（如果不存在）
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config.DB_NAME} CHARACTER SET utf8mb4")

            # 使用数据库
            await cursor.execute(f"USE {config.DB_NAME}")

            # 执行建表语句
            for sql in CREATE_TABLES_SQL.split(';'):
                if sql.strip():
                    await cursor.execute(sql)

    pool.close()
    await pool.wait_closed()

    # 连接具体数据库，插入测试数据
    db_pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        db=config.DB_NAME,
        charset='utf8mb4',
        ssl=ssl_ctx if ssl_ctx else None
    )

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 调用数据生成器
            await generate_all_data(cursor)
            await conn.commit()

    db_pool.close()
    await db_pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(init_database())
