"""`DatabaseQueryTool` 守卫 / LIMIT 注入 / 执行入口的纯单元测试（不连库）。

钉住 task15 评测发现的三个缺陷，防回归：
- **P2**：`_is_safe_query` 曾是子串黑名单（`'CREATE' ⊂ 'CREATED_AT'`）⇒ 合法 SELECT 被误杀。
  现改为「只允许 SELECT + 表白名单」的结构判据。
- **P0**：`execute_query` 曾调用已被删除的 `Database._get_connection` ⇒ 线上每次调用抛 AttributeError。
  现走 `Database.fetch_all`。
- **P3**：执行前无 LIMIT 就补 `MAX_ROWS`，防大结果集裸奔。

只 import `database_query` 与 `Database`，都是纯函数/无副作用的模块级对象。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database.db import Database  # noqa: E402
from app.tools.database_query import (  # noqa: E402
    MAX_ROWS,
    DatabaseQueryTool,
    _enforce_limit,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def tool():
    return DatabaseQueryTool()


# ───────────────────── P2 · 守卫：合法 SELECT 必须放行 ─────────────────────

@pytest.mark.parametrize("sql", [
    "SELECT MAX(created_at) FROM alarms",                 # 曾因 'CREATE' ⊂ 'CREATED_AT' 被误杀
    "SELECT updated_at FROM alarms ORDER BY created_at",
    "SELECT COUNT(*) FROM energy_consumption",
    "SELECT a.id, b.name FROM alarms a JOIN buildings b ON a.building_id = b.id",
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s",
    "SELECT TABLE_NAME FROM information_schema.tables",
])
def test_safe_selects_allowed(tool, sql):
    assert tool._is_safe_query(sql) is True


# ───────────────────── P2 · 守卫：非 SELECT / 非白名单语表必须拒 ─────────────────────

@pytest.mark.parametrize("sql", [
    "DELETE FROM alarms",
    "UPDATE alarms SET status = 'resolved'",
    "DROP TABLE alarms",
    "SELECT 1; DROP TABLE alarms",                       # 多语句
    "SELECT * FROM users",                               # 非白名单表
    "SELECT * FROM alarms -- 注释",
    "SELECT * FROM alarms WHERE id = 1 # 注释",
    "SELECT * FROM energy_consumption /* 注释 */",
])
def test_unsafe_or_non_whitelisted_rejected(tool, sql):
    assert tool._is_safe_query(sql) is False


def test_guard_is_pure_and_self_less():
    """守卫不读 self（诊断脚本 prove_blacklist_bug.py 以 self=None 调用它）。"""
    assert DatabaseQueryTool._is_safe_query(None, "SELECT 1 FROM buildings") is True


# ───────────────────── P3 · LIMIT 注入 ─────────────────────

def test_enforce_limit_appends_when_absent():
    out = _enforce_limit("SELECT * FROM energy_consumption")
    assert out == f"SELECT * FROM energy_consumption LIMIT {MAX_ROWS}"


def test_enforce_limit_strips_trailing_semicolon():
    out = _enforce_limit("SELECT * FROM energy_consumption;")
    assert out == f"SELECT * FROM energy_consumption LIMIT {MAX_ROWS}"


def test_enforce_limit_keeps_existing_limit():
    sql = "SELECT * FROM energy_consumption LIMIT 5"
    assert _enforce_limit(sql) == sql


# ───────────────────── P0 · execute_query 委托给 Database.fetch_all ─────────────────────

async def test_execute_query_uses_fetch_all_and_injects_limit(tool, monkeypatch):
    seen = {}

    async def fake_fetch_all(sql, params=None):
        seen["sql"] = sql
        seen["params"] = params
        return [{"n": 1}]

    monkeypatch.setattr(Database, "fetch_all", fake_fetch_all)
    rows = await tool.execute_query("SELECT COUNT(*) FROM energy_consumption")

    assert rows == [{"n": 1}]
    assert "LIMIT" in seen["sql"].upper()          # P3：补了 LIMIT
    assert seen["params"] is None


async def test_execute_query_passes_params(tool, monkeypatch):
    seen = {}

    async def fake_fetch_all(sql, params=None):
        seen["params"] = params
        return []

    monkeypatch.setattr(Database, "fetch_all", fake_fetch_all)
    await tool.execute_query("SELECT * FROM alarms WHERE building_id = %s", ("b1",))

    assert seen["params"] == ("b1",)


async def test_execute_query_rejects_unsafe_before_touching_db(tool, monkeypatch):
    called = False

    async def fake_fetch_all(sql, params=None):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(Database, "fetch_all", fake_fetch_all)
    with pytest.raises(ValueError):
        await tool.execute_query("DELETE FROM alarms")
    assert called is False
