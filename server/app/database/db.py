import aiomysql
from app.config import config

class Database:
    _pool = None

    @classmethod
    async def get_pool(cls):
        """获取数据库连接池单例"""
        if cls._pool is None:
            # 准备 SSL 配置（TiDB Cloud 需要）
            ssl_ctx = None
            
            # 检查是否配置了 SSL
            import os
            ssl_ca = os.getenv("SSL_CA")
            ssl_cert = os.getenv("SSL_CERT")
            ssl_key = os.getenv("SSL_KEY")
            
            # 如果是 TiDB Cloud，强制使用 SSL
            is_tidb_cloud = "tidbcloud.com" in config.DB_HOST.lower()
            
            if is_tidb_cloud or ssl_ca:
                try:
                    import ssl
                    
                    # 创建 SSL 上下文
                    ssl_ctx = ssl.create_default_context(cafile=ssl_ca) if ssl_ca else ssl.create_default_context()
                    
                    # 如果是 TiDB Cloud，设置 VERIFY_IDENTITY 模式
                    if is_tidb_cloud:
                        ssl_ctx.check_hostname = True
                        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
                    
                    # 如果有客户端证书，也加上
                    if ssl_cert and ssl_key:
                        ssl_ctx.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
                except Exception as e:
                    if is_tidb_cloud:
                        raise Exception(f"TiDB Cloud 必须配置 SSL 证书：{e}")
            
            cls._pool = await aiomysql.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                db=config.DB_NAME,
                minsize=5,
                maxsize=20,
                autocommit=True,
                charset='utf8mb4',
                ssl=ssl_ctx if ssl_ctx else None
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
        """执行 SQL（增删改）"""
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
                    # 处理 datetime 类型
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
