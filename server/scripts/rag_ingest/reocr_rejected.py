# server/scripts/rag_ingest/reocr_rejected.py
"""对 `pages.jsonl` 中 `source=="fail"` 的页**重跑 OCR**，产出 rejects_report.json。

动机（补 D28 的缺口）：闸门拒收的页在产物里只剩 `source="fail"` + `reject_reason`，
**看不到 OCR 到底读出了什么**。于是「英文目录页，正确剔除」和「OCR 炸了，真丢数据」
在下游产物里完全同形 —— 无法区分。本脚本只为**补证据**：重 OCR 这些页，记录
文本长度 / CJK 占比 / 判定 / 样例，让「为什么这页没进语料」可人工复核。

**明确不改语料**：不写 `pages.jsonl`、不写 `chunks.jsonl`、不碰检索索引。
本脚本的产出只有 `rejects_report.json`。

用法：
    cd server && python scripts/rag_ingest/reocr_rejected.py --out data/kb
"""
import argparse
import io
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

import pymupdf  # noqa: E402

import ingest_kb as ing  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description="重 OCR 闸门拒收页，产出 rejects_report.json（不改语料）")
    ap.add_argument("--out", default="./data/kb", help="含 pages.jsonl 的目录")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--report", default="", help="报告输出路径（默认 <out>/rejects_report.json）")
    ap.add_argument("--sample-chars", type=int, default=300, help="每页保留的 OCR 样例字数")
    args = ap.parse_args()

    pages_path = os.path.join(args.out, "pages.jsonl")
    if not os.path.exists(pages_path):
        print("找不到 %s —— 先在 server 目录跑 ingest_kb.py" % pages_path)
        return 1
    report_path = args.report or os.path.join(args.out, "rejects_report.json")

    rows = []
    with io.open(pages_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    fails = [r for r in rows if r.get("source") == "fail"]
    print("pages=%d  fail=%d  blank=%d  error=%d" % (
        len(rows), len(fails),
        sum(1 for r in rows if r.get("source") == "blank"),
        sum(1 for r in rows if r.get("source") == "error")), flush=True)
    # 空白页/异常页不在本次范围：前者是正确跳过（没内容可读），后者是抽页异常，
    # 与「OCR 读了但闸门拒收」不是同一类问题。
    if not fails:
        print("没有 fail 页，无需重 OCR")
        return 0

    if ing.get_ocr(args.threads) is None:
        print("OCR 引擎不可用（%s）→ 无法重 OCR" % ing._OCR_ERR)
        print("检查是否跑在项目 venv：D:\\Git_programs\\competitions\\.venv")
        return 1

    by_file = {}
    for r in fails:
        by_file.setdefault(r["file_idx"], []).append(r)

    recs = []
    t_all = time.time()
    for idx in sorted(by_file):
        rs = sorted(by_file[idx], key=lambda r: r["page"])
        fp = os.path.join(ing.PDF_DIR, rs[0]["file"])
        if not os.path.exists(fp):
            # PDF_DIR 是硬编码的本机绝对路径；换机器跑就会指空。
            print("  ! f%02d PDF 不存在：%s" % (idx, fp), flush=True)
            for r in rs:
                recs.append({
                    "file_idx": idx, "file": r["file"], "page": r["page"],
                    "reject_reason": r.get("reject_reason", ""),
                    "verdict": "pdf_missing", "ocr_text_len": 0,
                    "cjk": 0, "cjk_ratio": 0.0, "sample": "",
                })
            continue

        doc = pymupdf.open(fp)
        for r in rs:
            pno = r["page"]
            has_table = bool(r.get("has_table"))
            e = {
                "file_idx": idx, "file": r["file"], "page": pno,
                "reject_reason": r.get("reject_reason", ""),
                "has_table": has_table,
            }
            try:
                pix, dark, std = ing.render_gray(doc, pno, args.dpi)
            except Exception as ex:
                e.update({"verdict": "render_error", "ocr_text_len": 0,
                          "cjk": 0, "cjk_ratio": 0.0, "sample": "", "err": str(ex)})
                recs.append(e)
                continue

            if ing.is_blank(dark, std):
                # 重渲染后判为空白 ⇒ 原本就无内容可读，被拒是对的
                e.update({"verdict": "blank_like", "ocr_text_len": 0, "cjk": 0,
                          "cjk_ratio": 0.0, "sample": "",
                          "dark": round(dark, 5), "std": round(std, 2)})
                recs.append(e)
                continue

            t0 = time.time()
            otext, _ = ing.ocr_pix(pix, "%d_%d" % (idx, pno), args.threads)
            sec = time.time() - t0
            t2 = ing.strip_running_heads(ing.normalize(otext), has_table) if otext else ""
            ok2, diag2 = ing.page_usable(t2, min_cjk=10)
            cjk = diag2.get("cjk", 0)
            e.update({
                "ocr_text_len": len(t2),
                "cjk": cjk,
                "cjk_ratio": round(cjk / len(t2), 4) if t2 else 0.0,
                # re_ocr_passes：重跑却通过了闸门 —— 说明原来拒收可能是当时 OCR
                # 引擎不可用/抽页异常，属**可疑**，要重点看。
                "verdict": ("re_ocr_passes" if ok2
                            else ("ocr_empty" if not t2 else "gate_rejected")),
                "gate_reason": diag2.get("reason", ""),
                "sample": t2[:args.sample_chars],
                "dark": round(dark, 5), "std": round(std, 2), "sec": round(sec, 1),
            })
            recs.append(e)
            if (pno + 1) % 10 == 0:
                print("  f%02d %d/%d ..." % (idx, pno + 1, rs[-1]["page"] + 1), flush=True)
        doc.close()

    by_verdict = Counter(r["verdict"] for r in recs)
    by_reason = Counter(r.get("reject_reason") or r.get("gate_reason") or "?"
                        for r in recs)
    with_real = [r for r in recs if r.get("cjk", 0) >= 50]

    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_pages": pages_path,
        "note": "仅记录，不改 pages.jsonl / chunks.jsonl / 索引（补 D28 缺口）",
        "dpi": args.dpi,
        "n_pages": len(rows),
        "n_fail": len(fails),
        "by_verdict": dict(by_verdict),
        "by_reject_reason": dict(by_reason),
        "n_cjk_ge_50": len(with_real),
        "elapsed_sec": round(time.time() - t_all, 1),
        "pages": recs,
    }
    with io.open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\nREOCR fail=%d  verdicts=%s" % (len(fails), dict(by_verdict)), flush=True)
    print("拒收原因分布：%s" % dict(by_reason), flush=True)
    print("含真实中文（cjk>=50）的 fail 页：%d —— 这些才是**真丢内容**的重点审查对象"
          % len(with_real), flush=True)
    for r in with_real:
        print("  f%02d p%-4d reason=%-16s cjk=%d len=%d"
              % (r["file_idx"], r["page"], r.get("reject_reason") or r.get("gate_reason"),
                 r["cjk"], r["ocr_text_len"]), flush=True)
    print("\n报告 -> %s" % report_path, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
