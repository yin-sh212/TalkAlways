# app/services/rag_answer.py
"""线上 RAG 问答：检索国标语料 → 拼 prompt → 交给 LLM。

与 `rag_pipeline.py` 的区别：这里走的是**评测过的** hybrid 检索
（BM25 + 向量 + RRF + Cross-Encoder 重排），而不是旧 `vector_db` 纯向量路径。
参数默认值来自全量 394 问的端到端评测最优配置，见 task6_RAG/05_§7.2。
"""
from typing import Any, Dict, List

from app.config import config
from app.services.hybrid_retrieval import get_retriever

SNIPPET_CHARS = 120
_TITLE_KEYS = ("standard", "clause", "section", "chapter")


def _retriever_kwargs() -> Dict[str, Any]:
    return dict(
        chunks_path=config.RAG_CHUNKS_PATH,
        index_dir=config.RAG_INDEX_DIR,
        embed_model=config.RAG_EMBED_MODEL,
        rerank_model=config.RAG_RERANK_MODEL,
        use_rerank=True,
    )


def warmup():
    """构建/加载索引并**预热两个模型**，供启动阶段调用（阻塞）。

    只调 ensure_ready() 不够：embedding 与 reranker 都是懒加载，不预热的话
     第一个用户请求还要额外付一次模型加载。
    """
    retriever = get_retriever(**_retriever_kwargs())
    retriever._embed([""])
    retriever._get_reranker()
    return retriever


def _trigram_jaccard(a: str, b: str) -> float:
    """字符 3-gram Jaccard 相似度（0~1）。用于识别近重复片段。"""
    ga = {a[i:i + 3] for i in range(len(a) - 2)}
    gb = {b[i:i + 3] for i in range(len(b) - 2)}
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def _dedupe(hits: List[Dict[str, Any]], keep: int) -> List[Dict[str, Any]]:
    """贪心去近重复：按得分序保留，与已保留者 Jaccard >= 阈值则丢弃。

    D41：同一「失控条款单元」的兄弟段近重复且共享前缀（f05 附录 A 的表格被一个
    clause 单元吞掉、切成 113 段），一次检索的 5 条命中可能大半同源 —— 实测 3/5。
    折叠后剩下的才是来自不同位置的独立证据。
    """
    kept: List[Dict[str, Any]] = []
    for h in hits:
        content = h.get("content") or ""
        if any(_trigram_jaccard(content, k.get("content") or "") >= config.RAG_DEDUP_JACCARD
               for k in kept):
            continue
        kept.append(h)
        if len(kept) >= keep:
            break
    return kept


def retrieve(query: str) -> List[Dict[str, Any]]:
    """同步检索。调用方负责 `run_in_threadpool` 卸载，别阻塞事件循环。"""
    retriever = get_retriever(**_retriever_kwargs())
    # 超采：给近重复折叠留出替换空间，否则折叠后可能不足 TOP_K
    fetch = max(config.RAG_TOP_K, config.RAG_DEDUP_FETCH)
    hits = retriever.search(
        query,
        k=fetch,
        mode=config.RAG_MODE,
        pool=config.RAG_POOL,
        rrf_k=config.RAG_RRF_K,
        rrf_w_vector=config.RAG_W_VECTOR,
        rrf_w_bm25=config.RAG_W_BM25,
    )

    # 阈值门（B1）：top-1 重排分低于阈值 ⇒ 判为「没检索到相关内容」→ 降级。
    # 只对带 rerank_score 的模式生效（hybrid_rerank）；hybrid/bm25/vector 无此项。
    if config.RAG_MIN_RERANK > 0 and hits:
        top_score = hits[0].get("rerank_score")
        if top_score is not None and top_score < config.RAG_MIN_RERANK:
            return []

    hits = _dedupe(hits, config.RAG_TOP_K)
    return hits if len(hits) >= config.RAG_MIN_HITS else []


def build_prompt(query: str, hits: List[Dict[str, Any]]) -> str:
    """复用既有 RAG prompt 模板，避免两份模板各自漂移。"""
    # 函数内 import：rag_pipeline → vector_db 会在导入时加载 embedding 模型，
    # 放进来是为了让本模块能被轻量单测（见 tests/unit/test_rag_rrf_weights.py）
    from app.services.rag_pipeline import rag_pipeline

    return rag_pipeline.generate_prompt(query, hits)


def to_sources(hits: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """对齐前端已声明的 `AskResponse.sources = {id, title, snippet}`。"""
    sources: List[Dict[str, str]] = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        title = next((str(meta[k]) for k in _TITLE_KEYS if meta.get(k)), "")
        sources.append(
            {
                "id": hit.get("id", ""),
                "title": title or hit.get("id", ""),
                "snippet": (hit.get("content") or "")[:SNIPPET_CHARS],
            }
        )
    return sources
