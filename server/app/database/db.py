import os
import sys
import asyncio
import pymysql
from dotenv import load_dotenv
from app.config import config
from pathlib import Path

load_dotenv()

class Database:
    """
    数据库访问类 - 使用 PyMySQL（同步）+ 线程池
    原因：aiomysql 在 Windows 上与 TiDB Cloud 的 SSL 连接有兼容性问题
    """
    
    @staticmethod
    def _get_connection():
        """获取 PyMySQL 连接"""
        ssl_ca = os.getenv("SSL_CA")
        ssl_cert = os.getenv("SSL_CERT")
        ssl_key = os.getenv("SSL_KEY")
        
        # 转换相对路径为绝对路径
        if ssl_ca and not os.path.isabs(ssl_ca):
            ssl_ca = str(Path(__file__).parent.parent.parent / ssl_ca)
        
        # 准备 SSL 配置
        ssl_config = {}
        is_tidb_cloud = "tidbcloud.com" in config.DB_HOST.lower()
        
        if is_tidb_cloud or ssl_ca:
            if ssl_ca and os.path.exists(ssl_ca):
                ssl_config['ca'] = ssl_ca
                ssl_config['check_hostname'] = False
                ssl_config['verify_mode'] = True
            
            if ssl_cert and ssl_key:
                if not os.path.isabs(ssl_cert):
                    ssl_cert = str(Path(__file__).parent.parent.parent / ssl_cert)
                if not os.path.isabs(ssl_key):
                    ssl_key = str(Path(__file__).parent.parent.parent / ssl_key)
                
                if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
                    ssl_config['cert'] = ssl_cert
                    ssl_config['key'] = ssl_key
        
        return pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset='utf8mb4',
            autocommit=True,
            ssl=ssl_config if ssl_config else None,
            connect_timeout=10
        )
    
    @classmethod
    async def fetch_all(cls, query, params=None):
        """执行查询并返回所有结果"""
        loop = asyncio.get_event_loop()
        
        def _query():
            conn = cls._get_connection()
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cur:
                    cur.execute(query, params)
                    return cur.fetchall()
            finally:
                conn.close()
        
        return await loop.run_in_executor(None, _query)
    
    @classmethod
    async def fetch_one(cls, query, params=None):
        """执行查询并返回单条结果"""
        loop = asyncio.get_event_loop()
        
        def _query():
            conn = cls._get_connection()
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cur:
                    cur.execute(query, params)
                    return cur.fetchone()
            finally:
                conn.close()
        
        return await loop.run_in_executor(None, _query)
    
    @classmethod
    async def execute(cls, query, params=None):
        """执行 SQL 语句（INSERT/UPDATE/DELETE）"""
        loop = asyncio.get_event_loop()
        
        def _execute():
            conn = cls._get_connection()
            try:
                with conn.cursor() as cur:
                    result = cur.execute(query, params)
                    conn.commit()
                    return result
            finally:
                conn.close()
        
        return await loop.run_in_executor(None, _execute)
    
    @classmethod
    async def get_pool(cls):
        """获取数据库连接池（模拟 aiomysql 的接口）"""
        class PoolWrapper:
            def __init__(self):
                pass
            
            async def acquire(self):
                """获取连接"""
                conn = cls._get_connection()
                return ConnectionWrapper(conn)
        
        return PoolWrapper()


class ConnectionWrapper:
    """连接包装器，支持异步上下文管理器"""
    def __init__(self, conn):
        self.conn = conn
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
    
    async def rollback(self):
        """回滚事务"""
        self.conn.rollback()
    
    async def commit(self):
        """提交事务"""
        self.conn.commit()
    
    async def release(self):
        """释放连接"""
        self.conn.close()
    
    def cursor(self):
        """获取游标"""
        class CursorWrapper:
            def __init__(self, connection):
                self.cursor = connection.cursor()
            
            @property
            def rowcount(self):
                """代理 rowcount 属性"""
                return self.cursor.rowcount
            
            def __enter__(self):
                self.cursor.__enter__()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.cursor.__exit__(exc_type, exc_val, exc_tb)
            
            async def execute(self, query, params=None):
                if params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
                return self.cursor.rowcount
            
            async def fetchall(self):
                return self.cursor.fetchall()
            
            async def fetchone(self):
                return self.cursor.fetchone()
            
            # 添加异步上下文管理器支持
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.cursor.close()
        
        # 让 cursor() 方法本身也支持异步上下文管理器
        class AsyncCursorContextManager:
            def __init__(self, connection):
                self.connection = connection
            
            async def __aenter__(self):
                wrapper = CursorWrapper(self.connection)
                return wrapper
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return AsyncCursorContextManager(self.conn)
