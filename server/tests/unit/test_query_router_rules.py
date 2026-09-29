"""#13 最小路由（规则版）：四组信号 + abstain 默认。纯函数，毫秒级。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.query_router import route, route_or_default  # noqa: E402

pytestmark = pytest.mark.unit


def test_spec_question_goes_rag():
    assert route("冷库防火分区的划分要求是什么")["route"] == "rag"


def test_metric_question_goes_nl2sql():
    assert route("A 栋教学楼昨天的用电量是多少")["route"] == "nl2sql"


def test_entity_plus_metric_goes_nl2sql():
    assert route("三号配电箱本周负荷")["route"] == "nl2sql"


def test_both_signals_abstain():
    assert route("A 栋的用电量符合哪条规范要求")["route"] == "unknown"


def test_no_signal_abstains():
    assert route("你好")["route"] == "unknown"


def test_default_is_rag_on_abstain():
    assert route_or_default("你好") == "rag"
    assert route_or_default("A 栋的用电量符合哪条规范要求") == "rag"


def test_default_passes_through_nl2sql():
    assert route_or_default("A 栋教学楼昨天的用电量是多少") == "nl2sql"


def test_route_shape():
    r = route("冷库防火分区的划分要求是什么")
    assert set(r) == {"route", "reason", "matched_sql", "matched_rag"}
    assert r["matched_rag"]
