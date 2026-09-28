# server/scripts/rag_ingest/benchmark_ocr.py
"""
OCR 选型回测：用「有文本层的 PDF 页」当真值，渲染成图后跑 OCR，比对精度与速度。

用法:
    python benchmark_ocr.py --mode baseline        # 20 页 × 各引擎 @200dpi
    python benchmark_ocr.py --mode ablation        # DPI × 预处理 消融
结果写入 --out (默认 D:\\rag_bench\\result_*.json / .txt)
"""
import argparse
import io
import json
import os
import re
import time
import unicodedata
from typing import List, Tuple

import pymupdf

PDF_DIR = r"D:\竞赛\2026\服创\a08建筑能源智能管理与运营优化关键技术研究\建筑运维标准文档\规范标准"

# 有可用文本层的文件索引（见 选型文档 §1）
GT_FILE_INDICES = [4, 13, 14, 15, 17]
# 跳过封面/目录等前置页
SKIP_FRONT = 12


def is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿"


def norm(s: str) -> str:
    """归一化：NFKC 全角转半角 → 去水印 → 只保留字母数字与中文"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"www\.[A-Za-z0-9\.\-]+", "", s)
    s = re.sub(r"[A-Za-z0-9\.\-]*\.(com|cn|net)", "", s)
    return re.sub(r"[^\w一-鿿]", "", s, flags=re.UNICODE)


def cjk_count(s: str) -> int:
    return sum(1 for c in s if is_cjk(c))


def cjk_only(s: str) -> str:
    """只保留中文字符。用途：真值里内嵌的拉丁字母可能被字体映射成形近 CJK（见 D20 / diag_block），
    拿它比对是在测「真值坏没坏」而非「OCR 准不准」→ 主指标只比中文。"""
    return "".join(c for c in s if is_cjk(c))


# 形近 CJK 映射的码点集中区（见 02_决策日志.md D20）：
# 该区间内的字，干净文件里是正常中文（状/独/犬），坏文件里是拉丁字母的替换品
SUSPECT_LO, SUSPECT_HI = 0x7280, 0x72FF


def latin_suspect_ratio(text: str) -> float:
    """真值中「疑似拉丁字母被映射成形近 CJK」的浓度。
    干净文件 < 0.1%，file04 这类坏字体 ~3.8%（约 50 倍）。"""
    cps = [ord(c) for c in text if is_cjk(c)]
    if not cps:
        return 0.0
    return sum(1 for cp in cps if SUSPECT_LO <= cp <= SUSPECT_HI) / len(cps)


def gt_is_usable(text: str) -> bool:
    """真值页质量闸门：中文占比够高、无字形乱码、且是「真中文」"""
    if len(text.strip()) < 200:
        return False
    if re.search(r"/G[0-9A-F]{2}", text):
        return False
    if text.count("书") > 5:
        return False
    n = norm(text)
    if len(n) < 150:
        return False
    if cjk_count(n) / max(len(n), 1) <= 0.45:
        return False
    # 关键：字形乱码(如 犐犆犛)也落在 CJK 区间，会骗过占比检查。
    # 用「真实中文高频字」占比兜底 —— 正常中文行文必有这些字。
    common = sum(1 for c in n if c in COMMON_CHARS)
    return common / max(cjk_count(n), 1) > 0.10


COMMON_CHARS = set("的一是不了在人有我他这为之大来以个中上们到说国和地也子时道出而要于就下得可你年生自会那后能对着事其里所去行过家十用发天如然作方成者多日都三小军二无同么经法当起与好看学进种将还分此心前面又定见只主没公从")


def cer(pred: str, gt: str) -> float:
    """字符错误率；用 rapidfuzz 的编辑距离"""
    from rapidfuzz.distance import Levenshtein

    if not gt:
        return 1.0
    return Levenshtein.distance(pred, gt) / len(gt)


def collect_pages(per_pdf: int) -> List[dict]:
    """从 GT 文件里均匀抽页，返回 [{file, page, gt_text}]"""
    files = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    picked = []
    for idx in GT_FILE_INDICES:
        fp = os.path.join(PDF_DIR, files[idx])
        doc = pymupdf.open(fp)
        cand = []
        for pno in range(SKIP_FRONT, doc.page_count):
            t = doc[pno].get_text()
            if gt_is_usable(t):
                cand.append((pno, t))
        if cand:
            step = max(1, len(cand) // per_pdf)
            for j in range(0, len(cand), step):
                if len(picked) < per_pdf * len(GT_FILE_INDICES):
                    pno, t = cand[j]
                    picked.append({"file_idx": idx, "file": files[idx], "page": pno, "gt_text": t})
                if len([p for p in picked if p["file_idx"] == idx]) >= per_pdf:
                    break
        doc.close()
    return picked


def render(fp: str, pno: int, dpi: int, out_png: str):
    doc = pymupdf.open(fp)
    pix = doc[pno].get_pixmap(dpi=dpi)
    pix.save(out_png)
    doc.close()
    return out_png


def preprocess(png_path: str, mode: str) -> str:
    """原图 / 灰度 / 二值化，返回处理后的图片路径"""
    if mode == "raw":
        return png_path
    from PIL import Image

    out = png_path.replace(".png", f"_{mode}.png")
    im = Image.open(png_path).convert("L")
    if mode == "binary":
        im = im.point(lambda x: 0 if x < 160 else 255)
    im.save(out)
    return out


def run_rapidocr(engine, img_path: str) -> Tuple[str, float]:
    t0 = time.time()
    res, _ = engine(img_path)
    dt = time.time() - t0
    if not res:
        return "", dt
    return "".join(r[1] for r in res), dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="baseline", choices=["baseline", "ablation"])
    ap.add_argument("--pages-per-pdf", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--out", default=r"D:\rag_bench")
    ap.add_argument("--threads", type=int, default=0, help="onnxruntime intra_op 线程数；0=库默认")
    ap.add_argument("--det-limit", type=int, default=736, help="检测输入最长边上限；越小越快")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    img_dir = os.path.join(args.out, "images")
    os.makedirs(img_dir, exist_ok=True)

    pages = collect_pages(args.pages_per_pdf)
    print(f"GT pages collected: {len(pages)}", flush=True)

    from rapidocr_onnxruntime import RapidOCR

    kw = {"det_limit_side_len": args.det_limit}
    if args.threads:
        kw["intra_op_num_threads"] = args.threads
    try:
        engine = RapidOCR(**kw)
    except Exception as e:
        print("RapidOCR kwargs rejected (%s), falling back to defaults" % e, flush=True)
        engine = RapidOCR()

    # 预热：首帧含模型图优化，不计入统计
    if pages:
        warm_png = os.path.join(img_dir, "_warmup.png")
        render(os.path.join(PDF_DIR, pages[0]["file"]), pages[0]["page"], 200, warm_png)
        run_rapidocr(engine, warm_png)
        print("warmup done", flush=True)

    rows = []
    if args.mode == "baseline":
        for i, p in enumerate(pages):
            png = os.path.join(img_dir, "p%03d_f%d_pg%d_%ddpi.png" % (i, p["file_idx"], p["page"], args.dpi))
            render(os.path.join(PDF_DIR, p["file"]), p["page"], args.dpi, png)
            pred, dt = run_rapidocr(engine, png)
            gt_n, pred_n = norm(p["gt_text"]), norm(pred)
            acc = 1 - cer(pred_n, gt_n)
            # 主指标：只比中文（真值的拉丁字母可能被字体污染，见 D20）
            acc_cjk = 1 - cer(cjk_only(pred_n), cjk_only(gt_n))
            recall = cjk_count(pred_n) / max(cjk_count(gt_n), 1)
            susp = latin_suspect_ratio(p["gt_text"])
            rows.append({
                "file_idx": p["file_idx"],
                "page": p["page"],
                "gt_chars": len(gt_n),
                "pred_chars": len(pred_n),
                "acc_cjk": round(acc_cjk, 4),
                "accuracy": round(acc, 4),
                "cjk_recall": round(recall, 4),
                "latin_suspect": round(susp, 4),
                "sec": round(dt, 2),
            })
            print("  [%02d] f%d pg%-4d accCJK=%.3f accAll=%.3f rec=%.3f susp=%.3f %.1fs" % (
                i, p["file_idx"], p["page"], acc_cjk, acc, recall, susp, dt), flush=True)

        n = len(rows)
        clean = [r for r in rows if r["latin_suspect"] < 0.01]
        # 正文页：真值干净 且 召回率接近 1（召回偏离说明是图/表页，文本层与页面内容对不上，见 D8/D20）
        prose = [r for r in clean if abs(r["cjk_recall"] - 1.0) <= 0.05]
        secs_sorted = sorted(r["sec"] for r in rows)
        summary = {
            "engine": "RapidOCR (PP-OCRv4 mobile, onnxruntime)",
            "dpi": args.dpi,
            "pages": n,
            "mean_acc_cjk": round(sum(r["acc_cjk"] for r in rows) / n, 4),
            "mean_accuracy_all": round(sum(r["accuracy"] for r in rows) / n, 4),
            "mean_cjk_recall": round(sum(r["cjk_recall"] for r in rows) / n, 4),
            "mean_sec_per_page": round(sum(r["sec"] for r in rows) / n, 2),
            "median_sec_per_page": round(secs_sorted[len(secs_sorted) // 2], 2),
            "clean_pages": len(clean),
            "mean_acc_cjk_clean": round(sum(r["acc_cjk"] for r in clean) / len(clean), 4) if clean else None,
            "prose_pages": len(prose),
            "mean_acc_cjk_prose": round(sum(r["acc_cjk"] for r in prose) / len(prose), 4) if prose else None,
        }

    else:  # ablation
        grid = [(d, m) for d in (150, 200, 300) for m in ("raw", "gray", "binary")]
        # 均匀跨文件抽 5 页。注意：不能取 pages[:5] —— 那会全是文件 04（真值有缺陷，见 D20），
        # 消融结果会被单一文件的真值问题主导。
        _step = max(1, len(pages) // 5)
        sub = pages[::_step][:5]
        summary = {"engine": "RapidOCR", "grid": [], "pages": len(sub)}
        for dpi, mode in grid:
            accs, accs_cjk, recs, secs = [], [], [], []
            for i, p in enumerate(sub):
                png = os.path.join(img_dir, "ab_p%03d_f%d_pg%d_%ddpi.png" % (i, p["file_idx"], p["page"], dpi))
                render(os.path.join(PDF_DIR, p["file"]), p["page"], dpi, png)
                img = preprocess(png, mode)
                pred, dt = run_rapidocr(engine, img)
                gt_n, pred_n = norm(p["gt_text"]), norm(pred)
                accs.append(1 - cer(pred_n, gt_n))
                accs_cjk.append(1 - cer(cjk_only(pred_n), cjk_only(gt_n)))
                recs.append(cjk_count(pred_n) / max(cjk_count(gt_n), 1))
                secs.append(dt)
            cell = {
                "dpi": dpi, "preprocess": mode,
                "acc_cjk": round(sum(accs_cjk) / len(accs_cjk), 4),
                "accuracy": round(sum(accs) / len(accs), 4),
                "cjk_recall": round(sum(recs) / len(recs), 4),
                "sec_per_page": round(sum(secs) / len(secs), 2),
            }
            summary["grid"].append(cell)
            print("  dpi=%-4d %-7s accCJK=%.3f accAll=%.3f rec=%.3f %.2fs/page" % (
                dpi, mode, cell["acc_cjk"], cell["accuracy"],
                cell["cjk_recall"], cell["sec_per_page"]), flush=True)

    tag = args.mode
    with io.open(os.path.join(args.out, f"result_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows if args.mode == "baseline" else []}, f,
                  ensure_ascii=False, indent=2)
    print("\nSUMMARY:", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
