"""#12 改写的清洗与兜底：任何异常/垃圾输出都必须逐字退回原 query。

这是「失败 = 线上行为不变」的证据。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import config  # noqa: E402
from app.services import query_rewrite  # noqa: E402

pytestmark = pytest.mark.unit

_H = [{"role": "user", "content": "冷库防火分区的划分要求是什么"}]
_Q = "那它的限值呢？"


def _patch_return(monkeypatch, ret):
    monkeypatch.setattr(config, "RAG_REWRITE_ENABLED", True)
    monkeypatch.setattr(config, "RAG_REWRITE_LOG", False)
    monkeypatch.setattr(
        "app.services.llm_client.llm_client.chat", lambda *a, **k: ret
    )


def _patch_raise(monkeypatch):
    monkeypatch.setattr(config, "RAG_REWRITE_ENABLED", True)
    monkeypatch.setattr(config, "RAG_REWRITE_LOG", False)

    def _boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.services.llm_client.llm_client.chat", _boom)


def test_disabled_returns_original(monkeypatch):
    monkeypatch.setattr(config, "RAG_REWRITE_ENABLED", False)
    called = {"n": 0}
    monkeypatch.setattr(
        "app.services.llm_client.llm_client.chat",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or "X",
    )
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q
    assert called["n"] == 0


def test_no_history_never_calls_llm(monkeypatch):
    monkeypatch.setattr(config, "RAG_REWRITE_ENABLED", True)
    called = {"n": 0}
    monkeypatch.setattr(
        "app.services.llm_client.llm_client.chat",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or "X",
    )
    assert query_rewrite.rewrite_if_needed(_Q, []) == _Q
    assert called["n"] == 0


def test_none_return_falls_back(monkeypatch):
    _patch_return(monkeypatch, None)
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q


def test_empty_return_falls_back(monkeypatch):
    _patch_return(monkeypatch, "   \n  ")
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q


def test_apology_return_falls_back(monkeypatch):
    _patch_return(monkeypatch, "抱歉，我无法完成这个请求。")
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q


def test_overlong_return_falls_back(monkeypatch):
    _patch_return(monkeypatch, "冷库防火分区" * 40)
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q


def test_exception_falls_back(monkeypatch):
    _patch_raise(monkeypatch)
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q


def test_multiline_takes_first_line(monkeypatch):
    _patch_return(monkeypatch, "冷库防火分区的限值是多少\n\n解释：因为……")
    assert query_rewrite.rewrite_if_needed(_Q, _H) == "冷库防火分区的限值是多少"


def test_prefix_and_quotes_stripped(monkeypatch):
    _patch_return(monkeypatch, "改写结果：「冷库防火分区的限值是多少」")
    assert query_rewrite.rewrite_if_needed(_Q, _H) == "冷库防火分区的限值是多少"


@pytest.mark.parametrize("refusal", [
    "很抱歉，我无法完成这个请求。",
    "我无法确定你指的是什么。",
    "对不起，无法提供改写。",
])
def test_various_refusals_fall_back(monkeypatch, refusal):
    _patch_return(monkeypatch, refusal)
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q


def test_preamble_line_is_skipped(monkeypatch):
    _patch_return(monkeypatch, "好的，以下是改写结果：\n冷库防火分区的限值是多少")
    assert query_rewrite.rewrite_if_needed(_Q, _H) == "冷库防火分区的限值是多少"


def test_preamble_without_query_falls_back(monkeypatch):
    _patch_return(monkeypatch, "好的，以下是改写结果：")
    assert query_rewrite.rewrite_if_needed(_Q, _H) == _Q
