# server/scripts/rag_ingest/gen_eval_set.py
"""
用 LLM 从真实 chunk 反向生成评测集（问题 + 相关 chunk id 标注）。

设计：每个 chunk 生成**两类问题**，以便评测能暴露两种检索的强弱：
    semantic  语义型 —— 问法与原文字面不重合（向量该赢）
    keyword   编号/数值型 —— 含标准号、数值、专有名词（BM25 该赢）

用法:
    python gen_eval_set.py --chunks data/kb/chunks.jsonl --n 40 --out data/eval/eval_set.jsonl
"""
import argparse
import io
import json
import os
import random
import re
import sys
import time

import requests

# Windows 控制台默认 GBK。生成的问题里出现 `m³/h`、`m²` 这类字符时，进度 print 会抛
# UnicodeEncodeError；而 `--out` 只在**循环结束后**才写盘 → 整批问题全部丢失
# （实测 seed=43 这一批 100 问就是这么没的）。stdout 兜底成 UTF-8 + replace，
# 让编码问题最多只影响一条日志，不再能中断整批。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PDF_HINT = "建筑运维/暖通空调/建筑节能 国家标准或行业标准"


def get_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key
    # 退回读取 server/.env
    env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env):
        with io.open(env, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("未找到 DEEPSEEK_API_KEY")


PROMPT = """你是建筑运维领域的专家。下面是一段标准原文（来自{domain}）。

【原文】
{content}

请基于这段原文，生成 2 个用户**真实会问**的问题，要求：
1. semantic：语义型问题。用**口语化、与原文用词不同**的方式提问，答案需要理解原文语义才能得到。
2. keyword：编号/数值型问题。必须包含原文中出现的**标准编号、条款号、具体数值或专有名词**，答案在原文中字面可查。

严格要求：
- 两个问题都**必须**能从原文找到答案，不要问原文没写的东西。
- 不要出现"这段文字""原文""上述"等指代词。
- 只输出 JSON，不要任何其他文字。格式：
{{"semantic": "问题1", "keyword": "问题2"}}"""


def call_llm(key: str, prompt: str, retries: int = 3) -> dict:
    last = None
    for i in range(retries):
        try:
            r = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "response_format": {"type": "json_object"},
                },
                timeout=90,
            )
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            return json.loads(txt)
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=r"./data/kb/chunks.jsonl")
    ap.add_argument("--n", type=int, default=40, help="抽样 chunk 数（产出 2n 条问题）")
    ap.add_argument("--out", default=r"./data/eval/eval_set.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    with io.open(args.chunks, "r", encoding="utf-8") as f:
        chunks = [json.loads(l) for l in f if l.strip()]
    print("loaded chunks:", len(chunks), flush=True)

    # 只从「内容够长、像正文」的 chunk 里抽（跳过标题/页眉类短块）
    cand = [c for c in chunks if len(c["content"]) >= 120]
    print("candidates:", len(cand), flush=True)
    sample = random.sample(cand, min(args.n, len(cand)))

    key = get_key()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    rows, ok, fail = [], 0, 0
    for i, c in enumerate(sample):
        try:
            res = call_llm(key, PROMPT.format(domain=PDF_HINT, content=c["content"][:1200]))
        except Exception as e:
            fail += 1
            print("  [%02d] LLM FAIL %s" % (i, type(e).__name__), flush=True)
            continue
        for qtype in ("semantic", "keyword"):
            q = (res.get(qtype) or "").strip()
            if len(q) < 5:
                continue
            rows.append({
                "query": q,
                "type": qtype,
                "relevant_ids": [c["id"]],
                "source": (c.get("metadata") or {}).get("source", ""),
                "chunk_content": c["content"][:200],
            })
        ok += 1
        print("  [%02d/%d] %s" % (i + 1, len(sample), res.get("keyword", "")[:40]), flush=True)

    with io.open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("\n生成 %d 条问题（%d chunk 成功 / %d 失败）→ %s" % (len(rows), ok, fail, args.out))


if __name__ == "__main__":
    main()
