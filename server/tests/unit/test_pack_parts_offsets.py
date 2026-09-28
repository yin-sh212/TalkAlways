"""`pack_parts_with_offsets` 的纯单元测试（D41）。

三个断言：
1. **切分不变**：`pack_parts` 的输出与**冻结的旧实现**逐个相同 —— 否则重切会改
   id/内容，破坏已评测基线（197 条 gold / 05 数字失联）。
2. **偏移正确**：每个 part 的偏移指回它自己在原文中的位置（可用切片还原）。
3. 偏移单调不降。

只 import 摄取脚本，不建索引、不碰模型。
"""
import os
import re
import sys
from typing import List

import pytest

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _SERVER_ROOT)
sys.path.insert(0, os.path.join(_SERVER_ROOT, "scripts", "rag_ingest"))

from ingest_kb import pack_parts, pack_parts_with_offsets  # noqa: E402

pytestmark = pytest.mark.unit


def _frozen_old_pack_parts(text: str, max_chars: int) -> List[str]:
    """修复前的 `pack_parts` 原样拷贝，作为**回归基准**。

    必须留一份：`pack_parts` 现在是 offset 版本的薄包装，用它对 offset 版本做断言
    是**同义反复**，抓不到"切分点变了"这类 bug（开发中真的漏过一次：把阶段 1 的
    strip 推迟到阶段 2，导致 `rfind("。")` 在含前导空白的串上算切点，11 个真实
    chunk 的 content 变了，而当时的单测全绿）。
    """
    units = re.split(r"(?=\n\s*(?:\d{1,2}|[a-z]\)|[①-⑩])[\s、.])", text)
    parts, cur = [], ""
    for u in units:
        if cur and len(cur) + len(u) > max_chars:
            parts.append(cur.strip())
            cur = u
        else:
            cur += u
    if cur.strip():
        parts.append(cur.strip())
    out = []
    for p in parts:
        while len(p) > max_chars * 2:
            cut = p.rfind("。", 0, max_chars * 2)
            if cut < max_chars // 2:
                cut = max_chars * 2
            else:
                cut += 1
            out.append(p[:cut].strip())
            p = p[cut:]
        if p.strip():
            out.append(p.strip())
    return out


# 覆盖：条款边界、超长需按句号二次切、行首/行内空白、空行、无边界纯文本。
# 末尾两条是**已验证能触发**「strip 时机」差异的场景（开发中正是这类输入让
# 11 个真实 chunk 的 content 变了）：前导空白 + 无条款边界 + 超长需二次切。
# 注意并非任意"前导空白+超长"都能触发 —— 当空白长度与句号间距巧合对齐时，
# `.strip()` 会把偏移抵消掉（如 `'  \n   \n' + '前导空白后接超长正文。'*400`
# 就不触发）。所以这里留的是实测可触发的输入。
CASES = [
    "3.1.2 室内温度应符合下列规定：\n1 冬季不应低于 18℃；\n2 夏季不应高于 26℃。",
    "A.1 " + "气温数据。" * 400,
    "  \n  4.2.1   条文正文，前面有缩进和空行。  \n",
    "5.1 " + "句子。 " * 600 + "\n1 子项一；\n2 子项二；\n" + "又一段。" * 300,
    "没有任何编号的连续文本，" * 200,
    "",
    "   \n  \n",
    "7.7.7 " + "x" * 1000,
    " \n" + "甲乙丙。" * 400,                      # 实测触发（buggy 段数/长度都不同）
    "    \n" + "很长的句子内容在此。" * 300,          # 实测触发
]


@pytest.mark.parametrize("text", CASES)
def test_pack_parts_matches_frozen_old(text):
    """与**冻结的旧实现**逐字相同（真正的回归护栏，非同义反复）。"""
    assert pack_parts(text, 400) == _frozen_old_pack_parts(text, 400)


@pytest.mark.parametrize("text", CASES)
def test_offsets_match_pack_parts(text):
    """offset 版本的第一项必须与 pack_parts 逐个相同。"""
    assert pack_parts(text, 400) == [p for p, _ in pack_parts_with_offsets(text, 400)]


@pytest.mark.parametrize("text", CASES)
def test_offsets_point_at_part(text):
    """text[off : off+len(part)] == part —— 偏移确实指回该 part 自身。"""
    for part, off in pack_parts_with_offsets(text, 400):
        assert text[off:off + len(part)] == part, (repr(part[:20]), off)


@pytest.mark.parametrize("text", CASES)
def test_offsets_monotonic(text):
    """各 part 偏移严格不降 —— 保证页号回推单调（不会把后面的段落回标到前页）。"""
    offs = [off for _, off in pack_parts_with_offsets(text, 400)]
    assert offs == sorted(offs)
