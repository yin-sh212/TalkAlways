import aiomysql
from app.config import config

class Database:
    _pool = None

    @classmethod
    async def get_pool(cls):
        """获取数据库连接池单例"""
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                db=config.DB_NAME,
                minsize=5,
                maxsize=20,
                autocommit=True,
                charset='utf8mb4'
            )
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """关闭连接池"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None

    @classmethod
    async def execute(cls, sql: str, params: tuple = None):
        """执行SQL（增删改）"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params or ())
                return cursor.lastrowid

    @classmethod
    async def fetch_all(cls, sql: str, params: tuple = None):
        """查询多条数据"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, params or ())
                rows = await cursor.fetchall()
                # 获取列名
                columns = [desc[0] for desc in cursor.description]
                # 转为字典列表
                result = []
                for row in rows:
                    item = dict(zip(columns, row))
                    # 处理datetime类型
                    for key, value in item.items():
                        if hasattr(value, 'isoformat'):
                            item[key] = value.isoformat()
                    result.append(item)
                return result

    @classmethod
    async def fetch_one(cls, sql: str, params: tuple = None):
        """查询单条数据"""
        results = await cls.fetch_all(sql, params)
        return results[0] if results else None