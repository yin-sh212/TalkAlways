# server/scripts/rag_ingest/eval_retrieval.py
"""
检索评测：对比 纯向量 / BM25 / RRF混合 / RRF+rerank 的 Recall@K、Precision@K、MRR、Hit@K。

用法:
    python eval_retrieval.py --chunks data/kb/chunks.jsonl --eval data/eval/eval_set.jsonl
输出：控制台表格 + JSON（供回填文档）
"""
import argparse
import io
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.hybrid_retrieval import HybridRetriever  # noqa: E402

MODES = ["vector", "bm25", "hybrid", "hybrid_rerank"]
KS = [1, 3, 5, 10]

# 词法重合分桶：问题与该题 gold chunk 的 char-4gram 命中率。
# 为什么需要：semantic 题的重合度是**双峰**的（实测 14 题 <0.05、10 题 >=0.15），
# 均值 0.09 会把这两群混在一起，看不出「BM25 靠字面命中吃分」的部分有多少。
# 分层后可见：零重合题上向量反超 BM25 +0.222，聚合里的劣势全由高重合桶贡献。
OVERLAP_BUCKETS = [("low <0.05", 0.0, 0.05), ("mid 0.05-0.15", 0.05, 0.15),
                   ("high >=0.15", 0.15, 1.01)]


def ngrams(s, n=4):
    from collections import Counter
    s = "".join(ch for ch in s if not ch.isspace())
    return Counter(s[i:i + n] for i in range(len(s) - n + 1))


def lex_overlap(q, src):
    """问题里的 char-4gram 有多少比例在原文出现过。0 = 完全改写。"""
    gq, gs = ngrams(q), ngrams(src)
    if not gq:
        return 1.0
    return sum(min(v, gs.get(k, 0)) for k, v in gq.items()) / sum(gq.values())


def bucket_of(ov):
    for name, lo, hi in OVERLAP_BUCKETS:
        if lo <= ov < hi:
            return name
    return OVERLAP_BUCKETS[-1][0]


def load_jsonl(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def metrics_at_k(retrieved_ids, relevant, k):
    topk = retrieved_ids[:k]
    hit = [1 if i in relevant else 0 for i in topk]
    n_hit = sum(hit)
    recall = n_hit / max(len(relevant), 1)
    precision = n_hit / k
    return recall, precision, (1 if n_hit > 0 else 0)


def mrr(retrieved_ids, relevant):
    for rank, i in enumerate(retrieved_ids, 1):
        if i in relevant:
            return 1.0 / rank
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=r"./data/kb/chunks.jsonl")
    ap.add_argument("--eval", dest="eval_set", default=r"./data/eval/eval_set.jsonl")
    ap.add_argument("--index-dir", default=r"./data/hybrid_index")
    ap.add_argument("--embed-model", default="shibing624/text2vec-base-chinese")
    ap.add_argument("--rerank-model", default=r"D:\models\bge-reranker-base")
    ap.add_argument("--pool", type=int, default=20, help="每路召回候选数")
    ap.add_argument("--out", default=r"D:\rag_bench\retrieval_eval.json")
    args = ap.parse_args()

    eval_set = load_jsonl(args.eval_set)
    print("评测集: %d 条" % len(eval_set), flush=True)

    model = args.rerank_model if os.path.isdir(args.rerank_model) else "BAAI/bge-reranker-base"
    r = HybridRetriever(args.chunks, args.index_dir, args.embed_model, model, use_rerank=True)
    if not r.load():
        print("构建索引中（首次）...", flush=True)
        r.build()
        r.save()
    print("语料: %d chunks" % len(r.chunks), flush=True)

    results = {}
    src_by_id = {c["id"]: c["content"] for c in r.chunks}
    for mode in MODES:
        agg = defaultdict(list)
        by_type = defaultdict(lambda: defaultdict(list))
        by_overlap = defaultdict(lambda: defaultdict(list))
        for i, item in enumerate(eval_set):
            relevant = set(item["relevant_ids"])
            got = r.search(item["query"], k=max(KS), mode=mode, pool=args.pool)
            ids = [g["id"] for g in got]
            # 词法重合度：只对**语义题**有意义（keyword 题本来就要求含原文术语）
            ov = lex_overlap(item["query"], src_by_id.get(
                item["relevant_ids"][0], ""))
            ob = bucket_of(ov) if item.get("type") == "semantic" else None
            for k in KS:
                rec, prec, hit = metrics_at_k(ids, relevant, k)
                agg["recall@%d" % k].append(rec)
                agg["precision@%d" % k].append(prec)
                agg["hit@%d" % k].append(hit)
                by_type[item.get("type", "?")]["recall@%d" % k].append(rec)
                if ob:
                    by_overlap[ob]["recall@%d" % k].append(rec)
            agg["mrr"].append(mrr(ids, relevant))
            by_type[item.get("type", "?")]["mrr"].append(mrr(ids, relevant))
            if ob:
                by_overlap[ob]["mrr"].append(mrr(ids, relevant))
            if (i + 1) % 20 == 0:
                print("  %s: %d/%d" % (mode, i + 1, len(eval_set)), flush=True)

        results[mode] = {
            "overall": {m: round(sum(v) / len(v), 4) for m, v in agg.items()},
            "by_type": {
                t: {m: round(sum(v) / len(v), 4) for m, v in d.items()}
                for t, d in by_type.items()
            },
            "by_overlap": {
                b: dict({"n": len(d["mrr"])},
                        **{m: round(sum(v) / len(v), 4) for m, v in d.items()})
                for b, d in by_overlap.items()
            },
        }
        o = results[mode]["overall"]
        print("  [%s] R@1=%.3f R@5=%.3f R@10=%.3f MRR=%.3f" % (
            mode, o["recall@1"], o["recall@5"], o["recall@10"], o["mrr"]), flush=True)

    # 输出对比表
    lines = []
    lines.append("| 模式 | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR |")
    lines.append("|---|---|---|---|---|---|")
    for m in MODES:
        o = results[m]["overall"]
        lines.append("| %s | %.4f | %.4f | %.4f | %.4f | %.4f |" % (
            m, o["recall@1"], o["recall@3"], o["recall@5"], o["recall@10"], o["mrr"]))
    lines.append("")
    lines.append("| 模式 | 语义型 R@5 | 编号数值型 R@5 |")
    lines.append("|---|---|---|")
    for m in MODES:
        bt = results[m]["by_type"]
        lines.append("| %s | %.4f | %.4f |" % (
            m, bt.get("semantic", {}).get("recall@5", 0), bt.get("keyword", {}).get("recall@5", 0)))

    # 语义题按词法重合度分层：区分「真语义能力」与「靠字面命中吃分」
    lines.append("")
    lines.append("| 模式 | 语义·低重合 R@5 | 语义·中 R@5 | 语义·高重合 R@5 |")
    lines.append("|---|---|---|---|")
    for m in MODES:
        bo = results[m]["by_overlap"]
        lines.append("| %s | %.4f | %.4f | %.4f |" % (
            m,
            bo.get("low <0.05", {}).get("recall@5", 0),
            bo.get("mid 0.05-0.15", {}).get("recall@5", 0),
            bo.get("high >=0.15", {}).get("recall@5", 0)))

    table = "\n".join(lines)
    print("\n" + table, flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        json.dump({"results": results, "table": table,
                   "n_queries": len(eval_set), "n_chunks": len(r.chunks)}, f,
                  ensure_ascii=False, indent=2)
    print("\n→ %s" % args.out, flush=True)


if __name__ == "__main__":
    main()
