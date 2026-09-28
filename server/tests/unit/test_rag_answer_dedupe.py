"""`rag_answer` 的在线近重复折叠（D41）与 3-gram Jaccard 的纯单元测试。

只 import `rag_answer`：模块顶层不加载模型（`get_retriever` 在函数内调用），
`_dedupe` / `_trigram_jaccard` 都是纯函数，毫秒级。

阈值门（`RAG_MIN_RERANK`）需要真实 retriever 才能测，走端到端验证，不在此处。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import config  # noqa: E402
from app.services.rag_answer import _dedupe, _trigram_jaccard  # noqa: E402

pytestmark = pytest.mark.unit


def _hit(cid: str, content: str, score: float = 1.0):
    return {"id": cid, "content": content, "metadata": {}, "rerank_score": score}


# 内容多变的长文本（模拟附录表格段），不是重复单字符 —— 后者的 trigram 集合会塌成 1 个
_BASE = "".join(f"第{i}项 气温 数值 {i * 0.37:.2f} 度 | " for i in range(90))
_UNRELATED = "冷水机组高压报警时应先检查冷凝器散热与制冷剂充注量是否正常。" * 4


def test_jaccard_identical():
    assert _trigram_jaccard("冷水机组高压报警", "冷水机组高压报警") == 1.0


def test_jaccard_disjoint():
    assert _trigram_jaccard("冷水机组高压报警", "苹果公司今日股价上涨") == 0.0


def test_jaccard_short_strings_safe():
    """长度 < 3 时 trigram 集合为空，不能除零。"""
    assert _trigram_jaccard("", "abc") == 0.0
    assert _trigram_jaccard("ab", "ab") == 0.0


def test_siblings_are_near_duplicates():
    """共享长前缀的兄弟段应被判为近重复。"""
    assert _trigram_jaccard(_BASE + "尾部甲", _BASE + "尾部乙") >= config.RAG_DEDUP_JACCARD


def test_dedupe_collapses_siblings_keeps_distinct():
    hits = [
        _hit("a", _BASE + "尾部甲", 0.9),
        _hit("b", _BASE + "尾部乙", 0.8),   # a 的兄弟段 → 丢
        _hit("c", _UNRELATED, 0.7),         # 独立段 → 留
    ]
    kept = _dedupe(hits, keep=5)
    assert [h["id"] for h in kept] == ["a", "c"]


def test_dedupe_respects_keep_limit():
    hits = [_hit(f"h{i}", f"第{i}种互不相同的设备故障处置说明文字内容{i}", 1.0) for i in range(10)]
    assert len(_dedupe(hits, keep=3)) == 3


def test_dedupe_preserves_order():
    """保留下来的顺序必须仍是得分降序（去重只做剔除，不重排）。"""
    hits = [
        _hit("a", _UNRELATED, 0.9),
        _hit("b", _BASE + "尾部甲", 0.8),
        _hit("c", _BASE + "尾部乙", 0.7),
    ]
    assert [h["id"] for h in _dedupe(hits, keep=5)] == ["a", "b"]
