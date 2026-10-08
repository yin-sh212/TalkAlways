"""
数据库查询工具 - 为 AI Agent 提供安全的数据库访问能力
安全限制：只允许执行 SELECT 查询语句（白名单表 + 结构判据）
"""
import re
from typing import List, Dict, Any

from app.database.db import Database
from app.config import config

# 允许查询的表白名单（不含 users / knowledge_* / iot_* / *_new 等敏感或冗余表）
ALLOWED_TABLES = {
    "energy_consumption", "buildings", "meters", "devices",
    "alarms", "spaces", "floors", "alarm_types", "alarm_levels",
}

# 系统 schema：get_table_schema / get_available_tables 要从这里读元数据
_SYSTEM_SCHEMAS = {"information_schema"}

# 从 FROM / JOIN 后抓第一个标识符（含可选反引号），用于表白名单校验
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", re.I)

# 执行器强制上限：防「列出所有记录」把整表拉回内存
MAX_ROWS = 200


def _enforce_limit(sql: str, cap: int = MAX_ROWS) -> str:
    """没有 LIMIT 就补一个；已有 LIMIT 则原样返回。"""
    if re.search(r"\bLIMIT\b", sql, re.I):
        return sql
    return sql.rstrip().rstrip(";").strip() + f" LIMIT {cap}"


class DatabaseQueryTool:
    """AI 可调用的数据库查询工具"""

    def __init__(self):
        self.database_name = config.DB_NAME

    def _is_safe_query(self, sql: str) -> bool:
        """检查 SQL 是否安全：仅 SELECT + 无多语句/注释 + FROM/JOIN 表在白名单内。

        判危险靠「只允许 SELECT + 表白名单」这个结构约束，**不要用子串匹配**——
        例如 `'CREATE' in sql_upper` 会把合法的 `created_at` 列误判为建表语句。
        """
        s = (sql or "").strip().rstrip(";").strip()
        if not s.upper().startswith("SELECT"):
            return False
        # 尾部单个分号已剥掉；这里再出现分号 = 多语句。注释符一并禁。
        for bad in (";", "--", "/*", "#"):
            if bad in s:
                return False
        allowed = ALLOWED_TABLES | _SYSTEM_SCHEMAS | {config.DB_NAME.lower()}
        outside = [t for t in _TABLE_RE.findall(s) if t.lower() not in allowed]
        return not outside

    async def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行 SQL 查询（只读）

        Args:
            sql: SQL 查询语句
            params: 参数元组

        Returns:
            查询结果（每行为 dict，键为列名）

        Raises:
            ValueError: 如果 SQL 不安全
        """
        # 安全检查
        if not self._is_safe_query(sql):
            raise ValueError(f"不安全的 SQL 语句：{sql}")

        safe_sql = _enforce_limit(sql)
        try:
            return await Database.fetch_all(safe_sql, params)
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
