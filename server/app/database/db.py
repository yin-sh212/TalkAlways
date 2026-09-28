import os
import asyncio
import pymysql
import certifi
import threading
from queue import Queue, Empty
from dotenv import load_dotenv
from app.config import config
from pathlib import Path

load_dotenv()

POOL_SIZE = 5


def _build_ssl_config():
    ssl_ca = os.getenv("SSL_CA")
    ssl_cert = os.getenv("SSL_CERT")
    ssl_key = os.getenv("SSL_KEY")

    if ssl_ca and not os.path.isabs(ssl_ca):
        ssl_ca = str(Path(__file__).parent.parent.parent / ssl_ca)

    ssl_config = {}
    is_tidb_cloud = "tidbcloud.com" in config.DB_HOST.lower()

    if is_tidb_cloud or ssl_ca:
        if ssl_ca and os.path.exists(ssl_ca):
            ssl_config['ca'] = ssl_ca
            ssl_config['check_hostname'] = False
            ssl_config['verify_mode'] = True
        elif is_tidb_cloud:
            ssl_config['ca'] = certifi.where()

        if ssl_cert and ssl_key:
            if not os.path.isabs(ssl_cert):
                ssl_cert = str(Path(__file__).parent.parent.parent / ssl_cert)
            if not os.path.isabs(ssl_key):
                ssl_key = str(Path(__file__).parent.parent.parent / ssl_key)
            if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
                ssl_config['cert'] = ssl_cert
                ssl_config['key'] = ssl_key

    return ssl_config


def _create_connection():
    ssl_config = _build_ssl_config()
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


class _ConnectionPool:
    """线程安全的 PyMySQL 连接池"""
    def __init__(self, size=POOL_SIZE):
        self._pool = Queue(maxsize=size)
        self._lock = threading.Lock()
        self._created = 0
        self._size = size

    def _connect(self):
        conn = _create_connection()
        # 确保连接是活的
        conn.ping(reconnect=True)
        return conn

    def get(self):
        try:
            return self._pool.get_nowait()
        except Empty:
            with self._lock:
                if self._created < self._size:
                    self._created += 1
                    return self._connect()
            # 池满了，阻塞等待
            return self._pool.get(timeout=30)

    def put(self, conn):
        try:
            conn.ping(reconnect=True)
            self._pool.put_nowait(conn)
        except Exception:
            # 连接坏了，创建新的放回去
            try:
                conn.close()
            except Exception:
                pass
            try:
                self._pool.put_nowait(self._connect())
            except Exception:
                pass


_pool = _ConnectionPool()


class Database:

    @classmethod
    async def fetch_all(cls, query, params=None):
        loop = asyncio.get_event_loop()

        def _query():
            conn = _pool.get()
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cur:
                    cur.execute(query, params)
                    return cur.fetchall()
            finally:
                _pool.put(conn)

        return await loop.run_in_executor(None, _query)

    @classmethod
    async def fetch_one(cls, query, params=None):
        loop = asyncio.get_event_loop()

        def _query():
            conn = _pool.get()
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cur:
                    cur.execute(query, params)
                    return cur.fetchone()
            finally:
                _pool.put(conn)

        return await loop.run_in_executor(None, _query)

    @classmethod
    async def execute(cls, query, params=None):
        loop = asyncio.get_event_loop()

        def _execute():
            conn = _pool.get()
            try:
                with conn.cursor() as cur:
                    result = cur.execute(query, params)
                    conn.commit()
                    return result
            finally:
                _pool.put(conn)

        return await loop.run_in_executor(None, _execute)

    @classmethod
    async def get_pool(cls):
        class PoolWrapper:
            async def acquire(self):
                conn = _pool.get()
                return _ConnectionWrapper(conn)
        return PoolWrapper()


class _ConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        _pool.put(self.conn)

    async def rollback(self):
        self.conn.rollback()

    async def commit(self):
        self.conn.commit()

    async def release(self):
        _pool.put(self.conn)

    def cursor(self):
        class _CursorContext:
            def __init__(self, connection):
                self._conn = connection

            async def __aenter__(self):
                self._cursor = self._conn.cursor()
                return self._cursor

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self._cursor.close()

        return _CursorContext(self.conn)
