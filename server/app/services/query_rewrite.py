# app/services/query_rewrite.py
"""#12 · 检索前的 query 改写 / 指代消解。设计与决策见 task12_13_改写与路由/。"""
from typing import Dict, List, Optional

from app.config import config

# 「它」保留：它同时是「其它」的子串，会有少量误触发，但仍是最核心的代词。
# 故意不含裸「该」「其」「此」「他」「她」——「应该」「其中」「此外」「其他」是高频非指代词。
_PRONOUN_MARKERS = (
    "它", "它们",
    "这个", "那个", "这些", "那些",
    "这条", "那条", "这项", "那项",
    "该条", "该项", "该规范", "该标准", "该文件", "该表",
    "上述", "前述", "上面说的", "前面说的",
)


def needs_rewrite(query: str, history: Optional[List[Dict[str, str]]]) -> bool:
    """无历史或不像指代 → False。这是「单轮零额外调用」的唯一开关点。"""
    if not history:
        return False
    q = (query or "").strip()
    # 判短句时忽略标点：「为什么？」核心只有 3 字，是典型的依赖上文的追问
    core = q.strip("？?。.！!，,、；;：:…\"'“”「」『』 　")
    if len(core) <= 3:
        return True
    return any(m in q for m in _PRONOUN_MARKERS)


def build_rewrite_prompt(query: str, history: List[Dict[str, str]], max_turns: int) -> str:
    lines = []
    for turn in history[-max_turns:] if max_turns > 0 else history:
        role = "用户" if turn.get("role") == "user" else "助手"
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}：{content}")
    convo = "\n".join(lines)
    return (
        "下面是一段多轮对话，最后一句话是用户的新问题。"
        "请把它改写成一句**可以脱离上下文独立检索**的问题：\n"
        "1. 把其中的代词、省略（它／这个／那条／该规范…）还原成对话里出现过的具体实体；\n"
        "2. 实体**只能取自对话历史**，绝对不要编造历史里没有的名词；\n"
        "3. 如果新问题本身已经能独立检索，原样返回即可；\n"
        "4. **只输出改写后的那一句话**，不要解释、不要加引号、不要输出多行。\n\n"
        f"【对话历史】\n{convo}\n\n"
        f"【用户新问题】{query}\n\n"
        "【改写结果】"
    )


_REFUSAL_PREFIXES = (
    "抱歉", "很抱歉", "对不起", "我无法", "我不能", "无法回答", "无法提供", "无法确定",
)


def _clean(text: Optional[str], original: str) -> str:
    """把模型输出清洗成一行；任一可疑即返回 original。"""
    if not text:
        return original
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return original
    line = lines[0]

    # 「好的，以下是改写结果：」这类前置语：丢到下一非空行；没有下一行就退回 original
    if line.endswith(("：", ":")):
        line = lines[1] if len(lines) > 1 else ""
    if not line:
        return original

    for prefix in ("【改写结果】", "改写结果：", "改写后：", "改写："):
        if line.startswith(prefix):
            line = line[len(prefix):].strip()
    line = line.strip("「」『』\"'`“”").strip()
    if not line:
        return original

    if line.startswith(_REFUSAL_PREFIXES):
        return original
    if len(line) > max(60, 3 * len(original)):
        return original
    # 超长宁可退回原句，也不拦腰截断成残句
    if len(line) > 200:
        return original
    return line


def rewrite_if_needed(query: str, history: Optional[List[Dict[str, str]]]) -> str:
    """闸门 → 调用 → 清洗 → 兜底。失败时返回原始 query。"""
    if not config.RAG_REWRITE_ENABLED or not needs_rewrite(query, history):
        return query
    try:
        from app.services.llm_client import llm_client

        prompt = build_rewrite_prompt(query, history or [], config.RAG_REWRITE_HISTORY_TURNS)
        raw = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=config.RAG_REWRITE_TEMP,
            max_tokens=config.RAG_REWRITE_MAX_TOKENS,
            timeout=config.RAG_REWRITE_TIMEOUT,
        )
        out = _clean(raw, query)
        if config.RAG_REWRITE_LOG:
            print(f"[rewrite] {query!r} -> {out!r}")
        return out
    except Exception as exc:
        print(f"[rewrite] 失败，按原 query 检索：{exc}")
        return query
