"""离线冒烟：不启服务，直接验证 rag_answer 的预热 + 检索 + sources 形状。

用法（在 server/ 目录下）：
    ../.venv/Scripts/python.exe scripts/rag_ingest/smoke_rag_answer.py

首次运行会现场构建 data/hybrid_index（几分钟），之后只是加载。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# D39 第三条：日志必须能穿到文件。本脚本首次运行要构建索引（几分钟），
# 不加 flush 的话 stdout 全被缓冲，外部只能看到一行 requests 警告。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _log(msg=""):
    print(msg, flush=True)


from app.config import config  # noqa: E402
from app.services import rag_answer  # noqa: E402

QUERIES = [
    "GB 50736-2012 对空调室内设计温度的规定",   # 正例：应命中
    "冷水机组高压报警怎么处理",                  # 正例：应命中
    "今天天气怎么样",                            # 无关：应可能不命中
]


def main():
    _log(f"RAG_ENABLED={config.RAG_ENABLED} MODE={config.RAG_MODE} "
         f"POOL={config.RAG_POOL} RRF_K={config.RAG_RRF_K} "
         f"W_BM25:W_VECTOR={config.RAG_W_BM25}:{config.RAG_W_VECTOR} TOP_K={config.RAG_TOP_K}")
    _log(f"chunks={config.RAG_CHUNKS_PATH} index={config.RAG_INDEX_DIR}")
    _log(f"embed={config.RAG_EMBED_MODEL}\nrerank={config.RAG_RERANK_MODEL}\n")

    index_present = os.path.exists(os.path.join(config.RAG_INDEX_DIR, "index.faiss"))
    _log(f"[warmup] 索引{'已存在，直接加载' if index_present else '不存在，本次现场构建（数分钟）'}...")

    t0 = time.time()
    retriever = rag_answer.warmup()
    _log(f"[warmup] {time.time() - t0:.1f}s  chunks={len(retriever.chunks)}  "
         f"reranker={'loaded' if retriever._reranker is not None else 'MISSING'}\n")

    for q in QUERIES:
        t1 = time.time()
        hits = rag_answer.retrieve(q)
        dt = time.time() - t1
        sources = rag_answer.to_sources(hits)
        _log(f"[retrieve] {dt:6.1f}s  hits={len(hits)}  query={q!r}")
        for s in sources[:3]:
            _log(f"    - id={s['id']}  title={s['title']}  "
                 f"snippet={s['snippet'][:40]!r}")
        if hits:
            _log(f"    rerank_score[0]={hits[0].get('rerank_score')}")
            # 断言字段形状：前端 AskResponse.sources = {id, title, snippet}
            assert set(sources[0]) == {"id", "title", "snippet"}, sources[0]
        _log()

    if os.path.isdir(config.RAG_INDEX_DIR):
        _log("索引目录内容：" + json.dumps(os.listdir(config.RAG_INDEX_DIR), ensure_ascii=False))
    _log("\n冒烟通过")


if __name__ == "__main__":
    main()
