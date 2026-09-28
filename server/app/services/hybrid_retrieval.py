# app/services/hybrid_retrieval.py
"""
混合检索：BM25(关键词) + FAISS(向量) → RRF 融合 → Cross-Encoder 重排。

设计原则：**独立于现有 vector_db.py / rag_pipeline.py，不改动它们**，
避免破坏 ai_agent.py / ai_analyst.py、chat_api.py 现有引用。索引写入独立目录
（默认 data/hybrid_index），不覆盖线上 data/faiss_db。

检索模式：
    vector        纯向量（对照基线）
    bm25          纯关键词
    hybrid        BM25 + 向量 RRF 融合
    hybrid_rerank hybrid 融合后再用 Cross-Encoder 精排
"""
import hashlib
import io
import json
import os
import pickle
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

_STOPWORDS = set("的 了 和 与 及 或 在 是 为 对 于 以 之 其 该 等 把 被 而 则 也 就 都 很".split())
_CODE_RE = re.compile(r"[A-Za-z]{1,6}[\s\-]?\d+(?:\.\d+)*")


def _jieba():
    import jieba

    jieba.setLogLevel(60)
    return jieba


def tokenize(text: str) -> List[str]:
    """中文分词 + 保留标准编号（GB 50736-2012 / DB37/T 5095）。"""
    toks: List[str] = []
    for t in _jieba().lcut(text or ""):
        t = t.strip().lower()
        if not t or t in _STOPWORDS:
            continue
        if not re.search(r"[\w一-鿿]", t):
            continue
        toks.append(t)
    # 标准号整体保留：分词会把 "GB50736" 切碎，影响关键词命中
    toks += [m.lower().replace(" ", "") for m in _CODE_RE.findall(text or "")]
    return toks


def load_chunks(path: str) -> List[Dict[str, Any]]:
    """读取语料。支持 .jsonl（每行一条）与 .pkl（list[dict]）。"""
    if path.endswith(".jsonl"):
        out = []
        with io.open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out
    with open(path, "rb") as f:
        data = pickle.load(f)
    return list(data)


class HybridRetriever:
    """BM25 + 向量 双路检索，RRF 融合，可选 Cross-Encoder 重排。"""

    def __init__(
        self,
        chunks_path: str,
        index_dir: str = "./data/hybrid_index",
        embed_model: str = "shibing624/text2vec-base-chinese",
        rerank_model: str = "BAAI/bge-reranker-base",
        use_rerank: bool = True,
    ):
        self.chunks_path = chunks_path
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        self.embed_model_name = embed_model
        self.rerank_model_name = rerank_model
        self.use_rerank = use_rerank

        self.chunks: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self.bm25 = None
        self.faiss_index = None
        self._embedder = None
        self._reranker = None
        # 串行化检索：FAISS 查询只读安全，但 torch 推理在多线程下各自开 intra-op
        # 线程、争抢 CPU 并抬内存峰值；锁住换来的是吞吐而非仅安全。
        self._search_lock = threading.Lock()

    # ---------- 构建 ----------

    def build(self) -> int:
        """从 chunks 建 BM25 与 FAISS 索引。"""
        self.chunks = load_chunks(self.chunks_path)
        if not self.chunks:
            raise ValueError(f"语料为空: {self.chunks_path}")
        self.ids = [c.get("id") or ("c%06d" % i) for i, c in enumerate(self.chunks)]

        docs_tok = [tokenize(c["content"]) for c in self.chunks]
        from rank_bm25 import BM25Okapi

        self.bm25 = BM25Okapi(docs_tok)

        embs = self._embed([c["content"] for c in self.chunks])
        import faiss

        # L2 归一化后内积 == 余弦相似度（修正线上 vector_db 未归一化的问题）
        faiss.normalize_L2(embs)
        self.faiss_index = faiss.IndexFlatIP(embs.shape[1])
        self.faiss_index.add(embs)
        return len(self.chunks)

    @staticmethod
    def _file_sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        return h.hexdigest()

    def _src_sig(self) -> Dict[str, Any]:
        """索引所依赖语料的指纹。语料一变指纹就变，load() 据此判失效。"""
        try:
            return {"sha256": self._file_sha256(self.chunks_path), "count": len(self.chunks)}
        except OSError:
            return {}

    def save(self):
        import faiss

        faiss.write_index(self.faiss_index, os.path.join(self.index_dir, "index.faiss"))
        with open(os.path.join(self.index_dir, "bm25.pkl"), "wb") as f:
            pickle.dump(
                {
                    "bm25": self.bm25,
                    "ids": self.ids,
                    "chunks": self.chunks,
                    "src_sig": self._src_sig(),
                },
                f,
            )

    def load(self) -> bool:
        ip = os.path.join(self.index_dir, "index.faiss")
        bp = os.path.join(self.index_dir, "bm25.pkl")
        if not (os.path.exists(ip) and os.path.exists(bp)):
            return False
        with open(bp, "rb") as f:
            d = pickle.load(f)

        # 语料指纹校验：索引必须由**当前** chunks 文件构建。缺失或不符都判失效，
        # 交给调用方重建。不校验会静默用旧语料作答 —— 且重启后依然复现（比进程内
        # 缓存更隐蔽）。旧版本索引没有 src_sig，一律视为失效、重建一次即可。
        sig = d.get("src_sig")
        if not sig or not os.path.exists(self.chunks_path):
            return False
        if sig.get("sha256") != self._file_sha256(self.chunks_path):
            return False

        import faiss

        self.faiss_index = faiss.read_index(ip)
        self.bm25, self.ids, self.chunks = d["bm25"], d["ids"], d["chunks"]
        return True

    def ensure_ready(self) -> bool:
        if self.load():
            return True
        ok = bool(self.build())
        if ok:
            self.save()  # 重建后必须落盘（含指纹），否则每次运行都重建
        return ok

    # ---------- 懒加载模型 ----------

    def _embed(self, texts: List[str]) -> np.ndarray:
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(self.embed_model_name)
        return np.asarray(
            self._embedder.encode(texts, normalize_embeddings=False), dtype="float32"
        )

    def _get_reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder

            self._reranker = CrossEncoder(self.rerank_model_name)
        return self._reranker

    # ---------- 单路检索 ----------

    def search_vector(self, query: str, k: int = 20) -> List[Tuple[str, float]]:
        emb = self._embed([query])
        import faiss

        faiss.normalize_L2(emb)
        k = min(k, len(self.ids))
        sims, idxs = self.faiss_index.search(emb, k)
        return [(self.ids[i], float(s)) for s, i in zip(sims[0], idxs[0]) if i >= 0]

    def search_bm25(self, query: str, k: int = 20) -> List[Tuple[str, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)[: min(k, len(scores))]
        return [(self.ids[i], float(scores[i])) for i in order]

    # ---------- 融合 ----------

    @staticmethod
    def rrf(
        ranked_lists: List[List[Tuple[str, float]]],
        k: int = 60,
        weights: Optional[List[float]] = None,
    ) -> List[Tuple[str, float]]:
        """Reciprocal Rank Fusion。k=60 为工业界经验值。

        weights 与 ranked_lists 逐路对应，缺省等权；按常数整体缩放不改排序。
        """
        if weights is None:
            weights = [1.0] * len(ranked_lists)
        # 长度不匹配必须显式报错：zip 会静默截断，产出「看着正常」的错误排序 ——
        # 与 D36 记的「权重谁配谁」属同一类口径坑，宁可炸也不要静默算错。
        if len(weights) != len(ranked_lists):
            raise ValueError(
                f"weights 必须与 ranked_lists 逐路对应："
                f"{len(weights)} 个权重 vs {len(ranked_lists)} 路排名"
            )
        acc: Dict[str, float] = {}
        for w, lst in zip(weights, ranked_lists):
            for rank, (doc_id, _) in enumerate(lst, 1):
                acc[doc_id] = acc.get(doc_id, 0.0) + w / (k + rank)
        return sorted(acc.items(), key=lambda x: -x[1])

    def _by_id(self, doc_id: str) -> Dict[str, Any]:
        for i, cid in enumerate(self.ids):
            if cid == doc_id:
                return self.chunks[i]
        return {}

    def _fmt(self, ranked: List[Tuple[str, float]]) -> List[Dict[str, Any]]:
        out = []
        for doc_id, score in ranked:
            c = self._by_id(doc_id)
            out.append(
                {
                    "id": doc_id,
                    "content": c.get("content", ""),
                    "metadata": c.get("metadata", {}),
                    "score": float(score),
                }
            )
        return out

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        model = self._get_reranker()
        pairs = [(query, c["content"]) for c in candidates]
        scores = model.predict(pairs)
        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)
        return sorted(candidates, key=lambda x: -x["rerank_score"])[:top_n]

    # ---------- 统一入口 ----------

    def search(
        self,
        query: str,
        k: int = 5,
        mode: str = "hybrid_rerank",
        pool: int = 20,
        rrf_k: int = 60,
        rrf_w_vector: float = 1.0,
        rrf_w_bm25: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Args:
            k: 返回条数
            mode: vector | bm25 | hybrid | hybrid_rerank
            pool: 每路召回候选数（融合/重排前的池子，也是重排深度）
            rrf_k: RRF 常数，决定「加权能改多少次序」的分辨率。k 越小，两路
                权重的杠杆越大：实测融合 top-20 的变动量 k=10 约 3.5 条、
                k=5 约 3.0 条，而 **k=60（工业界经验值）只有约 1.9 条** ——
                权重几乎调不动排序，端到端 R@20 也卡死在纯 bm25 的水平
                （`05 §7.2`）。故线上取 `k=5` 而非默认 60。
                探针：`D:\rag_bench\probe_rrf_k_mechanism.py`
            rrf_w_vector / rrf_w_bm25: 融合时两路权重。**具名参数**，避免
                「谁在前」的口径歧义（`05 §7.1` 记过这个坑）
        """
        with self._search_lock:
            if mode == "vector":
                return self._fmt(self.search_vector(query, pool)[:k])
            if mode == "bm25":
                return self._fmt(self.search_bm25(query, pool)[:k])

            fused = self.rrf(
                [self.search_vector(query, pool), self.search_bm25(query, pool)],
                k=rrf_k,
                weights=[rrf_w_vector, rrf_w_bm25],
            )
            if mode == "hybrid":
                return self._fmt(fused[:k])
            if mode == "hybrid_rerank":
                if not self.use_rerank:
                    return self._fmt(fused[:k])
                cands = self._fmt(fused[:pool])
                return self.rerank(query, cands, k)
            raise ValueError(f"未知模式: {mode}")


_instance: Optional[HybridRetriever] = None
_init_lock = threading.Lock()


def get_retriever(
    chunks_path: str = "./data/kb/chunks.jsonl",
    index_dir: str = "./data/hybrid_index",
    **kw,
) -> HybridRetriever:
    """全局单例，避免重复加载模型。

    锁内二次判空：两个并发首请求若各自 build，会同时往同一份
    `bm25.pkl` / `index.faiss` 写，可能写出损坏的索引文件。
    """
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                retriever = HybridRetriever(chunks_path, index_dir, **kw)
                retriever.ensure_ready()
                _instance = retriever
    return _instance
