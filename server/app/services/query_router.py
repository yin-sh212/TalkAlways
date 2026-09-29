# app/services/query_router.py
"""#13 · 最小单路径路由：RAG（国标语料）vs NL2SQL（数据库）。

规则版，零成本、可单测。**只做单选一条路**；跨路径问题不在范围内。
判定信号、默认偏 RAG 的理由见 task12_13_改写与路由/。
"""
import re
from typing import Any, Dict, List

_SQL_SIGNALS = (
    "多少", "几", "指标", "数值", "统计", "同比", "环比", "趋势", "走势", "排名", "top",
    "用电量", "耗电量", "耗能量", "能耗", "电量", "度数", "千瓦时", "kwh", "功率",
    "电费", "水费", "费用", "金额", "占比", "平均", "总和", "日均", "峰值", "峰谷",
    "报表", "日报", "周报", "月报", "逐时", "明细", "记录数", "最近", "本周", "上周",
    "本月", "上月", "去年", "今年", "昨天", "今天", "前天",
)

_RAG_SIGNALS = (
    "规范", "标准", "gb", "jgj", "条文", "条款", "术语", "定义", "限值", "附录",
    "防火", "防雷", "节能设计", "荷载", "应符合", "不应", "不得", "强制性",
    "划分", "什么是", "规定", "要求",
)

# 实体槽位（建筑/设备/日期）：补「实体 + 指标名词」这种无显式指标词的查库意图
_ENTITY_RE = re.compile(
    r"([一-龥A-Za-z0-9]{1,8}(栋|号楼|楼|大厦|园区|校区|配电箱|配电柜|"
    r"冷水机组|冷机|水泵|机组|空调|电表|水表))"
    r"|(\d{4}[-/年]\d{1,2})"
)
_METRIC_NOUNS = ("能耗", "用电", "耗电", "用水", "水耗", "电量", "电费", "功率", "负荷")


def _has_entity_slot(query: str) -> bool:
    return bool(_ENTITY_RE.search(query or ""))


def _has_metric_noun(query: str) -> bool:
    return any(n in query for n in _METRIC_NOUNS)


def _result(route_: str, reason: str, sql_hits: List[str], rag_hits: List[str]) -> Dict[str, Any]:
    return {
        "route": route_,
        "reason": reason,
        "matched_sql": sql_hits,
        "matched_rag": rag_hits,
    }


def route(query: str) -> Dict[str, Any]:
    """返回 {"route": "rag"|"nl2sql"|"unknown", "reason", "matched_sql", "matched_rag"}。

    `unknown` 是保留的 abstain 桶（供统计覆盖率），最终决定看 `route_or_default`。
    """
    q = (query or "").strip().lower()
    rag_hits = [s for s in _RAG_SIGNALS if s in q]
    sql_hits = [s for s in _SQL_SIGNALS if s in q]

    if not sql_hits and _has_entity_slot(query or "") and _has_metric_noun(q):
        sql_hits = ["实体+指标"]

    if rag_hits and not sql_hits:
        return _result("rag", "只命中规范/条文信号", sql_hits, rag_hits)
    if sql_hits and not rag_hits:
        return _result("nl2sql", "只命中指标/数据信号", sql_hits, rag_hits)
    if not rag_hits and not sql_hits:
        return _result("unknown", "无信号", sql_hits, rag_hits)
    return _result("unknown", "双信号", sql_hits, rag_hits)


def route_or_default(query: str) -> str:
    """最终决定：`unknown` → `rag`。"""
    r = route(query)["route"]
    return "rag" if r == "unknown" else r
