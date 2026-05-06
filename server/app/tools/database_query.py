"""
数据库查询工具 - 为 AI Agent 提供安全的数据库访问能力
安全限制：只允许执行 SELECT 查询语句
"""
from typing import List, Dict, Any, Optional
from app.database.db import Database
from app.config import config


class DatabaseQueryTool:
    """AI 可调用的数据库查询工具"""
    
    def __init__(self):
        self.database_name = config.DB_NAME
    
    def _is_safe_query(self, sql: str) -> bool:
        """检查 SQL 是否安全（只允许 SELECT）"""
        sql_upper = sql.strip().upper()
        
        # 只允许 SELECT 开头的语句
        if not sql_upper.startswith('SELECT'):
            return False
        
        # 禁止包含危险关键字
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'REPLACE',
            'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        return True
    
    async def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行 SQL 查询（只读）
        
        Args:
            sql: SQL 查询语句
            params: 参数元组
            
        Returns:
            查询结果列表
            
        Raises:
            ValueError: 如果 SQL 不安全
        """
        # 安全检查
        if not self._is_safe_query(sql):
            raise ValueError(f"不安全的 SQL 语句：{sql}")
        
        try:
            conn = Database._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except Exception as e:
            print(f"[DatabaseQueryTool] 查询执行失败：{e}")
            raise
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表结构（帮助 AI 生成正确的 SQL）
        
        Args:
            table_name: 表名
            
        Returns:
            列信息列表
        """
        sql = """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        return await self.execute_query(sql, (self.database_name, table_name))
    
    async def get_available_tables(self) -> List[Dict[str, str]]:
        """
        获取所有可用的表信息
        
        Returns:
            表信息列表（包含表名和注释）
        """
        sql = """
            SELECT TABLE_NAME, TABLE_COMMENT
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
        """
        return await self.execute_query(sql, (self.database_name,))


# 全局实例
db_tool = DatabaseQueryTool()
