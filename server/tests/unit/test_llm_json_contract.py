"""钉住「让模型稳定吐 JSON」的两件套：json_mode 接线 + extract_json/输出契约。

不连网、不连库：requests.post 被 monkeypatch，模型只做纯校验。
"""
import pytest

from app.services.ai_agent import Analysis, Insight, QueryPlan, _coerce
from app.services.llm_client import LLMClient, extract_json

pytestmark = pytest.mark.unit


class _FakeResp:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _patch_post(monkeypatch, captured: dict):
    def fake_post(url, headers=None, json=None, **kwargs):
        captured.clear()
        captured.update(json or {})
        return _FakeResp('{"ok": 1}')

    monkeypatch.setattr("app.services.llm_client.requests.post", fake_post)


@pytest.fixture
def client():
    c = LLMClient()
    c.deepseek_api_key = "test-key"
    return c


# ── A：json_mode 必须 opt-in ─────────────────────────────────────────────
def test_json_mode_sets_response_format(client, monkeypatch):
    captured = {}
    _patch_post(monkeypatch, captured)
    client.generate("请返回 JSON", json_mode=True)
    assert captured["response_format"] == {"type": "json_object"}


def test_prose_mode_does_not_set_response_format(client, monkeypatch):
    """关键回归钉：聊天/报告类自然语言调用绝不能被塞进 JSON 模式。"""
    captured = {}
    _patch_post(monkeypatch, captured)
    client.generate("请聊聊今天的能耗情况")
    assert "response_format" not in captured


# ── B：extract_json 的边界 ───────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"queries": [{"table": "t", "sql": "SELECT 1"}]}\n```',
     {"queries": [{"table": "t", "sql": "SELECT 1"}]}),
    ('好的，结果如下：{"answer": "ok"} 希望有帮助', {"answer": "ok"}),
    ('["a", "b"]', ["a", "b"]),
])
def test_extract_json_happy(text, expected):
    assert extract_json(text) == expected


@pytest.mark.parametrize("text", ["", "抱歉，我无法回答。", "{不是合法json}", None])
def test_extract_json_returns_none(text):
    assert extract_json(text) is None


# ── 输出契约：默认值必须与下游 .get(key, default) 一致 ────────────────────
def test_query_plan_ignores_extra_fields():
    plan = QueryPlan.model_validate(
        {"queries": [{"table": "alarms", "sql": "SELECT 1", "junk": 1}], "extra": 2}
    )
    assert plan.queries[0].table == "alarms"
    assert plan.queries[0].sql == "SELECT 1"
    assert not hasattr(plan, "extra")


def test_analysis_defaults_match_consumer_expectations():
    a = Analysis.model_validate({})
    assert a.answer == "未获取到分析结果"
    assert a.follow_ups == []
    assert a.chart_type == "table"
    assert a.confidence == 0.8


def test_insight_coerces_numeric_strings():
    ins = Insight.model_validate({"estimated_savings_kwh": "120", "priority": "HIGH"})
    assert ins.estimated_savings_kwh == 120.0
    assert ins.priority == "HIGH"


def test_coerce_returns_raw_when_validation_fails():
    """单个字段类型走样 → 退回原始 dict，而不是把整段回答变成一句报错。"""
    raw = {"answer": "ok", "confidence": None}  # None 不是合法 float
    assert _coerce(Analysis, raw) == raw
