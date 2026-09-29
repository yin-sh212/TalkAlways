"""#12 指代消解触发器（needs_rewrite）真值表。纯函数，毫秒级。

这是「单轮零额外 LLM 调用」的证据：没有 history（单轮）时恒 False。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.query_rewrite import needs_rewrite  # noqa: E402

pytestmark = pytest.mark.unit

_H = [{"role": "user", "content": "冷库防火分区的划分要求是什么"}]


def test_no_history_never_rewrites():
    assert needs_rewrite("那它的限值呢？", []) is False
    assert needs_rewrite("那它的限值呢？", None) is False


def test_pronoun_triggers():
    assert needs_rewrite("那它的限值呢？", _H) is True
    assert needs_rewrite("该标准怎么说", _H) is True
    assert needs_rewrite("上述条款的适用条件", _H) is True


def test_very_short_triggers():
    assert needs_rewrite("那呢？", _H) is True
    assert needs_rewrite("为什么？", _H) is True


def test_self_contained_does_not_trigger():
    assert needs_rewrite("冷库防火分区的划分要求是什么", _H) is False


def test_bare_non_anaphoric_chars_do_not_trigger():
    """裸「该/其/此/他/她」不触发（应/其/此/他 都是高频非指代词）。"""
    for q in ["应该怎么处理", "其他建筑的能耗", "其中包含哪些条款", "此外还有什么"]:
        assert needs_rewrite(q, _H) is False
