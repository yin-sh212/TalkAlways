"""`split_clauses` 的 body→源文本偏移映射 `body_off_to_full_off`（D41 续修）。

为什么单独测：`body` **不是** `full` 的连续切片 ——
  1. 章标题 / 附录标题行会被**丢弃**（两条 continue），丢弃处产生**空洞**；
  2. 条文号独占一行时 `rest` 为空，随后空行会给 body 加前导 `\\n`，`flush()` 的
     strip 再把它剪掉（body_idx 整体左移）；
  3. OCR 行尾常带空格，行首偏移只能用**前导**空白算，不能 `len(ln)-len(strip)`。
任何一条做错，`start + part_off` 回推页码都会**累积**误差（实测 f05 附录 A 达到整页），
而 body 内容/id 都不变，故无法被"内容等价"类断言发现。这几个用例逐一锁死上述结构。
"""
import os
import sys

import pytest

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _SERVER_ROOT)
sys.path.insert(0, os.path.join(_SERVER_ROOT, "scripts", "rag_ingest"))

from ingest_kb import (  # noqa: E402
    body_off_to_full_off, is_cjk, pack_parts_with_offsets, split_clauses,
)

pytestmark = pytest.mark.unit


def _cjk(s: str) -> int:
    return sum(1 for c in s if is_cjk(c))


def _mapped_parts(text: str):
    """复刻 ingest 的取 part 逻辑，返回 [(unit, part, off_in_body, off_in_full), ...]。"""
    out = []
    for u in split_clauses(text):
        if not u["clause"]:
            continue
        body = u["body"].strip()
        if len(body) < 12:
            continue
        for part, off in pack_parts_with_offsets(body, 400):
            if _cjk(part) < 6:
                continue
            out.append((u, part, off, body_off_to_full_off(u, off)))
    return out


# 1) 无陷阱的普通文本（回归护栏：别把正常情况改坏）
PLAIN = "3.1.2 室内温度应符合下列规定：\n1 冬季不应低于 18℃；\n2 夏季不应高于 26℃。\n"

# 2) 条文号独占一行 + 空行 → body 前导 \\n 被 strip（曾使 body_idx 整体错位）
REST_EMPTY_BLANK = (
    "3.2\n \n \n本条正文内容足够长，用于测试前导空白被 strip 时的偏移映射是否仍然正确。\n"
)

# 3) OCR 行尾空格 → 行首偏移只能减**前导**空白（曾误减尾部空白致右移）
TRAILING_WS = (
    "4.1 本条正文后面带了 OCR 常见的行尾空格，需要正确计算行首偏移。   \n"
    "继续一段同样带行尾空格的内容，确保偏移不会因尾部空白而右移。  \n"
)

# 4) 单元中途**插入被丢弃的附录标题** → body 出现空洞；且正文够长切成多段，
#    使"空洞之后的那个 part"暴露 `start + off` 的累积漂移。
GAP = (
    "3.1 " + "第一部分正文内容。" * 30 + "\n"
    "附录 A 气温参数表\n"
    + "第二部分正文内容出现在被丢弃的附录标题之后。" * 25 + "\n"
)

CASES = [PLAIN, REST_EMPTY_BLANK, TRAILING_WS, GAP]


@pytest.mark.parametrize("text", CASES)
def test_produces_parts(text):
    assert _mapped_parts(text), "用例应至少产出一个 clause part"


@pytest.mark.parametrize("text", CASES)
def test_mapped_offset_points_at_part_start(text):
    """映射偏移处的字符 == part 首字符 —— 这正是页码归属所需的不变量。"""
    for u, part, off, fo in _mapped_parts(text):
        assert text[fo] == part[0], (
            "clause=%r off=%d fo=%d text[fo]=%r part[0]=%r"
            % (u["clause"], off, fo, text[fo:fo + 10], part[:10])
        )


@pytest.mark.parametrize("text", CASES)
def test_mapped_offsets_monotonic_within_unit(text):
    """同一单元内，part 偏移在源文本中必须单调不降（页码不会被回标到前页）。

    不能断言整段逐字还原：body 会丢行尾空白、丢「条文行→续行」的换行、丢标题行，
    这些都在行边界制造非连续（既有行为，与本次修复无关）。故只锁"哪一页"所需的
    起点不变量 + 单调性。
    """
    by_unit = {}
    for u, part, off, fo in _mapped_parts(text):
        by_unit.setdefault(id(u), []).append((off, fo))
    assert by_unit
    for pairs in by_unit.values():
        fos = [fo for _, fo in sorted(pairs)]
        assert fos == sorted(fos), fos


def test_dropped_header_makes_naive_offset_drift():
    """空洞存在时，旧的 `start + off` 必然漂移 —— 证明本用例确有区分力。

    若将来有人把 `body_off_to_full_off` 改回 `u["start"] + off`，
    `test_mapped_offset_points_at_part_start` 会对 GAP 失败；此处再显式断言
    "朴素公式与精确映射不同"，避免该用例被悄悄弱化。
    """
    diffs = [
        (u["start"] + off) - fo
        for u, part, off, fo in _mapped_parts(GAP)
    ]
    assert any(d != 0 for d in diffs), "GAP 用例未能触发朴素公式漂移，用例已失效"
