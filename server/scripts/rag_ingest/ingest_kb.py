# server/scripts/rag_ingest/ingest_kb.py
"""
建筑标准 PDF → 条文级 chunk（data/kb/chunks.jsonl）

设计依据：D:\课程精华\简历\task6_RAG\01_预处理选型.md §6
- 逐页 pymupdf 取文本 → 字形修复 → 页级清洗 → 质量闸门 → 不合格才 OCR
- 每份文件把可用页**拼回全文**再按条文切分（条款会跨页，逐页切会切出残句）
- 逐页落盘（pages.jsonl）→ 可断点续跑（全量 ~5h）

用法:
    python ingest_kb.py --files 4,13,15 --max-pages 25 --out D:\\rag_bench\\kb_smoke
    python ingest_kb.py --files all --out data/kb           # 全量
    python ingest_kb.py --files all --resume --out data/kb   # 续跑
    python ingest_kb.py --chunk-only --out data/kb           # 只重切分，不重跑 OCR
"""
import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata
from typing import Dict, List, Optional, Tuple

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PDF_DIR = r"D:\竞赛\2026\服创\a08建筑能源智能管理与运营优化关键技术研究\建筑运维标准文档\规范标准"

# ---------------------------------------------------------------- 字形修复
# 某些标准 PDF 的字体 ToUnicode 表把拉丁字母映射成形近 CJK（见 02_决策日志.md D20）。
# 这份表由全语料扫描得到：20 份 PDF 逐页扫 U+7280–U+72FF，用上下文反推字母，
# 498 处出现全部落在 file04，共 27 个「字母」码点。
#
# ⚠️ 同区间还含**真中文**：状 U+72B6(138次) / 独 U+72EC(77次) / 犬 U+72AC / 犷 U+72B7。
#    所以**只能按码点白名单替换，绝不能整区间替换** —— 否则把真中文改成字母。
#    （D20 那条「n→狀 U+72B6」是错的：n 实为 U+72C0 狀(繁体)，U+72B6 是简体的「状」。
#      这正是 D20 教训本身 —— 判错就把「该修的数据」和「正常数据」搞混。）
LOOKALIKE_LETTERS = {
    0x7283: "A", 0x7285: "B", 0x7286: "C", 0x728C: "G", 0x7290: "I",
    0x7296: "N", 0x7298: "P", 0x729B: "S", 0x729C: "T",
    0x72AA: "a", 0x72AE: "c", 0x72B1: "d", 0x72B2: "e", 0x72B3: "f",
    0x72B5: "g", 0x72BB: "i", 0x72BE: "l", 0x72BF: "m", 0x72C0: "n",
    0x72C5: "o", 0x72C6: "p", 0x72C7: "q", 0x72C9: "r", 0x72CA: "s",
    0x72CB: "t", 0x72CC: "u", 0x72CF: "v",
}
REAL_CJK_IN_RANGE = {0x72AC: "犬", 0x72B6: "状", 0x72B7: "犷", 0x72EC: "独"}


def repair_lookalikes(text: str) -> Tuple[str, int]:
    """把形近 CJK 还原成拉丁字母。返回 (修复后文本, 替换次数)"""
    if not text:
        return text, 0
    out, n = [], 0
    for ch in text:
        rep = LOOKALIKE_LETTERS.get(ord(ch))
        if rep is None:
            out.append(ch)
        else:
            out.append(rep)
            n += 1
    return "".join(out), n


def letter_suspect_ratio(text: str) -> float:
    """「字母码点」占比（精确版）。比 benchmark_ocr 的区间版更准：
    区间版把 状/独 也算可疑，导致 file04 修复后仍报 ~2.5%。"""
    cps = [ord(c) for c in text if "一" <= c <= "鿿"]
    if not cps:
        return 0.0
    return sum(1 for cp in cps if cp in LOOKALIKE_LETTERS) / len(cps)


# ---------------------------------------------------------------- 文本规整
def normalize(text: str) -> str:
    """NFKC：全角数字/字母→半角（f15/f17 条文号是全角，不转没法切）。
    另修「数字间用中文句号」的编号（3。2。1 → 3.2.1，f13 出现过）。
    只规整空白，**不删标点**（chunk 要保留可读性）。"""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"(?<=\d)。(?=\d)", ".", t)
    t = re.sub(r"[ \t　]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿"


COMMON_CHARS = set("的一是不了在人有我他这为之大来以个中上们到说国和地也子时道出而要于就下得可你年生自会那后能对着事其里所去行过家十用发天如然作方成者多日都三小军二无同么经法当起与好看学进种将还分此心前面又定见只主没公从")

# 页眉/页脚：单独成行的标准号（如 GB/T40571—2021、DB37/T 2671—2019）
HEADER_STD_RE = re.compile(r"^[A-Z]{2,4}(?:/[A-Z]{1,2})?\s?\d{1,5}(?:[.\-—]\d+)*$")
BARE_NUM_RE = re.compile(r"^\d{1,4}$")


def strip_running_heads(text: str, has_table: bool) -> str:
    """去掉页眉/页脚：标准号行、以及首尾的孤立页码。
    页码只在**非表页**的首尾各 2 行内删（表页里的独立数字是数据值，不能删）。"""
    lines = text.split("\n")
    out = [l for l in lines if not HEADER_STD_RE.match(l.strip())]
    if not has_table:
        idx = [i for i, l in enumerate(out) if l.strip()]
        edge = set(idx[:2]) | set(idx[-2:])
        out = [l for i, l in enumerate(out) if not (i in edge and BARE_NUM_RE.match(l.strip()))]
    return "\n".join(out)


# 目录前导符：不同文件用了不同字符 —— . / !(f15,f17 的乱码目录) / ·(中点) / ⋯
# 必须匹配「连续 ≥4 个」的**串**，不能只数单个字符 ——
# 表页满是小数（0.7143、0.25…），只数单字符会把表页误判成目录（踩过：f18 7/16 页被误杀）。
TOC_LEADER_RUN_RE = re.compile(r"[.!·⋯…]{4,}")


def is_toc_page(text: str) -> bool:
    """目录页：≥3 段前导符串。目录页无正文价值，且会切出
    「5.1 分类 5.1 分类2 ......」或「10.4 维修····40」这类垃圾 chunk。"""
    return len(TOC_LEADER_RUN_RE.findall(text)) >= 3


def page_usable(text: str, min_cjk: int = 30) -> Tuple[bool, Dict]:
    """摄取用质量闸门（比 benchmark 的 gt_is_usable 宽松：不要求 200 字）"""
    # reason 记录**是哪一条判据**拒收的（D28）。没有它，「闸门正确剔除索引页」和
    # 「OCR 炸了导致丢页」在下游产物里完全同形 —— 都是 source="fail"、text=""。
    info = {"cjk": 0, "common": 0.0, "suspect": 0.0, "glyph": False, "reason": ""}
    if not text:
        info["reason"] = "empty"
        return False, info
    info["cjk"] = sum(1 for c in text if is_cjk(c))
    if info["cjk"] < min_cjk:
        info["reason"] = "cjk_lt_%d" % min_cjk
        return False, info
    if re.search(r"/G[0-9A-F]{2}", text):
        info["glyph"] = True
        info["reason"] = "cid_glyph"
        return False, info
    info["suspect"] = letter_suspect_ratio(text)
    if info["suspect"] > 0.005:
        info["reason"] = "suspect_gt_0.005"
        return False, info
    cjk_chars = [c for c in text if is_cjk(c)]
    if not cjk_chars:
        info["reason"] = "no_cjk"
        return False, info
    info["common"] = sum(1 for c in cjk_chars if c in COMMON_CHARS) / len(cjk_chars)
    # 阈值 0.02（原为 0.08）。本检查只为排除「几乎没有真实中文」的页（英文目录 cjk=0、
    # 乱码碎片），不是要求「读起来像散文」。表格页满是数值/单位/专有名词，高频虚词天然
    # 稀少（实测 0.02~0.08）——0.08 会把「变压器能效等级表」「照明功率密度限值表」整页
    # 丢掉，而那正是「查具体数值」最该保住的语料。字形乱码另由 suspect / \G[0-9A-F]{2} 兜住。
    if info["common"] <= 0.02:
        info["reason"] = "common_le_0.02"
        return False, info
    info["reason"] = "ok"
    return True, info


# ---------------------------------------------------------------- OCR
_OCR = None


_OCR_ERR = None


def get_ocr(threads: int = 0):
    """惰性加载 OCR。返回 None 表示不可用 —— 调用方要能降级，
    不能让「OCR 装不上」把整页（含可用文本层）都判成 error（踩过：跑错解释器）。"""
    global _OCR, _OCR_ERR
    if _OCR is not None:
        return _OCR
    if _OCR_ERR:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR

        if threads:
            try:
                _OCR = RapidOCR(intra_op_num_threads=threads)
            except Exception:
                _OCR = RapidOCR()
        else:
            _OCR = RapidOCR()
    except Exception as e:
        _OCR_ERR = "%s: %s" % (type(e).__name__, e)
    return _OCR


def render_gray(doc, pno: int, dpi: int):
    """渲染灰度图（D21 选定的预处理）并算墨迹密度。
    实测空白页 dark≈0.000/std≈0.4，最稀疏的正文页 dark≈0.011/std≈16 —— 分离度 25 倍，
    所以能安全地跳过空白页，不必白花 ~4s/页的 OCR 推断。"""
    import numpy as np

    pix = doc[pno].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    return pix, float((arr < 200).mean()), float(arr.std())


def is_blank(dark: float, std: float) -> bool:
    return dark < 0.003 and std < 5.0


def ocr_pix(pix, tag: str, threads: int) -> Tuple[str, float]:
    """对已渲染的图跑 OCR。引擎不可用或单页失败 → 返回空串，由调用方降级。"""
    import tempfile

    engine = get_ocr(threads)
    if engine is None:
        return "", 0.0
    t0 = time.time()
    tmp = os.path.join(tempfile.gettempdir(), "ingest_%s.png" % tag)
    try:
        pix.save(tmp)
        res, _ = engine(tmp)
        return ("".join(r[1] for r in res) if res else ""), time.time() - t0
    except Exception:
        return "", time.time() - t0
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------- 表格检测
def page_has_table(page) -> bool:
    """轻量启发式：短行占比高 + 数字 token 多 → 判为表页。
    不用 page.find_tables()：纯文本页上也慢，且对扫描件无效。"""
    lines = [l.strip() for l in page.get_text().split("\n") if l.strip()]
    if len(lines) < 8:
        return False
    short = sum(1 for l in lines if len(l) <= 14)
    nums = sum(1 for l in lines if re.fullmatch(r"[<>=≤≥]?\s*\d+(?:\.\d+)?", l))
    return short / len(lines) > 0.45 and nums >= 5


# ---------------------------------------------------------------- 条文切分
# 条文号：正文 X.Y / X.Y.Z / X.Y.Z.W，附录 A.1 / B.1.2（字母开头）。
# 每段限 1–2 位数字 + 末尾边界断言 —— 否则表格数值「0.7143」会被当成条文号 0.71。
CLAUSE_RE = re.compile(
    r"^((?:[A-Z]|\d{1,2})(?:\.\d{1,2}){1,3})(?=\s|[^\d.]|$)\s*[ 　]*(.*)$")
CHAPTER_RE = re.compile(r"^(\d{1,2})\s+(\S.{0,20})$")
# 附录标题：附录 A / 附 录 B / Appendix C —— 必须重置 section，
# 否则附录条文会被挂到上一章末尾的「节」breadcrumb 上（如「8.2 风险分析 A.3.1 ...」）
APPENDIX_RE = re.compile(r"^(?:附\s*录\s*[A-Z]|Appendix\s*[A-Z])")


def split_clauses(text: str) -> List[Dict]:
    """按条文号切分，记录各 unit 在 text 中的起始偏移（用于回推页码）。
    粒度为「节(X.Y)」与「条(X.Y.Z)」；章标题(X+短标题)只记 breadcrumb，不单独成 chunk。

    `segs`：body 内偏移 ↔ `text` 内偏移的**分段映射** `[(body_idx, text_off), ...]`。
    body 会丢弃章/附录标题行（见下方两处 continue），因此 body **不是** `text` 的连续切片；
    直接用 `start + part_off` 回推页码会随丢弃行数**累积误差**（D41 修正：f05 附录 A 的
    长单元里累积了 859 字符 ⇒ 整页错位）。逐行记下每行首字符在 text 中的偏移方可精确回推。
    """
    lines = text.split("\n")
    units: List[Dict] = []
    chapter = section = ""
    cur: Optional[Dict] = None
    off = 0

    def flush():
        nonlocal cur
        if cur and cur["body"].strip():
            raw = cur["body"]
            lead = len(raw) - len(raw.lstrip())
            cur["body"] = raw.strip()
            # body 被 strip 掉前导空白时，segs 的 body_idx 要同步左移；被整段吞掉的
            # 段（idx<lead）直接丢弃 —— 只影响空白，不影响任何正文偏移。
            if lead:
                cur["segs"] = [(bi - lead, fo) for bi, fo in cur["segs"] if bi - lead >= 0]
            units.append(cur)
        cur = None

    for ln in lines:
        s = ln.strip()
        step = len(ln) + 1
        # 本行首字符（去**前导**空白后）在 text 中的偏移。必须只减前导空白：
        # 用 `len(ln)-len(s)` 会把**尾部**空白也算进去 ⇒ 偏移右移（OCR 行尾常带空格，
        # 实测 f13/f14/f17/f18 上千处错位）。body 首字符无前导空白，故 flush() 的
        # strip（仅尾部）不会打乱已记下的 body_idx。
        ln_off = off + (len(ln) - len(ln.lstrip()))
        if not s:
            if cur:
                cur["body"] += "\n"
            off += step
            continue
        m = CLAUSE_RE.match(s)
        if m:
            no, rest = m.group(1), m.group(2)
            # 「节」= X.Y（正文）或 X.1（附录，如 A.1、B.2）→ 作为 breadcrumb
            if no.count(".") == 1:
                section = s[:40]
            flush()
            # rest 为空（条文号独占一行）时不记 seg —— 否则会记下指向其后 "\n" 的
            # 退化映射，与下一行的真 seg 撞同一个 body_idx。
            cur = {"clause": no, "depth": no.count(".") + 1, "chapter": chapter,
                   "section": section, "body": rest, "start": off,
                   "segs": ([(0, ln_off + (len(s) - len(rest)))] if rest else [])}
            off += step
            continue
        if APPENDIX_RE.match(s):
            chapter, section = s[:40], ""
            off += step
            continue
        mc = CHAPTER_RE.match(s)
        if mc and len(s) <= 24 and not re.search(r"[。；，、：]$", s):
            chapter, section = s[:40], ""
            off += step
            continue
        if cur:
            cur["segs"].append((len(cur["body"]), ln_off))
            cur["body"] += s + "\n"
        else:
            cur = {"clause": "", "depth": 0, "chapter": chapter,
                   "section": section, "body": s + "\n", "start": off,
                   "segs": [(0, ln_off)]}
        off += step
    flush()
    return units


def body_off_to_full_off(u: Dict, body_off: int) -> int:
    """把 unit `body` 内的偏移映射回源文本内的偏移（用 `split_clauses` 记下的 `segs`）。
    无 segs（外部手工构造的 unit）时退化为旧行为 `start + body_off`。"""
    segs = u.get("segs")
    if not segs:
        return u["start"] + body_off
    base = None
    for bi, fo in segs:
        if bi <= body_off:
            base = (bi, fo)
        else:
            break
    if base is None:
        return u["start"] + body_off
    return base[1] + (body_off - base[0])


def pack_parts_with_offsets(text: str, max_chars: int) -> List[Tuple[str, int]]:
    """同 `pack_parts` 的切分，额外返回每个 part 首字符在 `text` 中的偏移。

    偏移用于给每个 part 标**它自己所在的页**（D41：一个 clause 单元可能横跨多页，
    旧实现把整个单元的所有 part 都标成单元**起点**页 ⇒ 引用指错页）。返回的
    字符串与 `pack_parts` 逐个相同，只是多了第二项。
    """
    # re.split 用零宽前瞻切分 ⇒ units 顺序拼接还原 text，可据此累加偏移
    units = re.split(r"(?=\n\s*(?:\d{1,2}|[a-z]\)|[①-⑩])[\s、.])", text)
    unit_offsets, acc = [], 0
    for u in units:
        unit_offsets.append(acc)
        acc += len(u)

    def lead_ws(s: str) -> int:
        return len(s) - len(s.lstrip())

    # 阶段 1：按 max_chars 粗分组。注意**此处就 strip**（与旧实现一致）——
    # 若把 strip 推到阶段 2，阶段的 `rfind("。")` 会在含前导空白的串上算切点，
    # 切出的分段与旧实现不同（实测会让 11 个 chunk 的 content 变化）。
    parts: List[Tuple[str, int]] = []  # (已 strip 的组文本, 组首字符在 text 中的偏移)
    cur, cur_start = "", 0
    for u, off in zip(units, unit_offsets):
        if cur and len(cur) + len(u) > max_chars:
            parts.append((cur.strip(), cur_start + lead_ws(cur)))
            cur, cur_start = u, off
        else:
            if not cur:
                cur_start = off
            cur += u
    if cur.strip():
        parts.append((cur.strip(), cur_start + lead_ws(cur)))

    # 阶段 2：超长组再按句号切，逐段推进 base
    out: List[Tuple[str, int]] = []
    for p, base in parts:
        while len(p) > max_chars * 2:
            cut = p.rfind("。", 0, max_chars * 2)
            if cut < max_chars // 2:
                cut = max_chars * 2
            else:
                cut += 1
            seg = p[:cut]
            out.append((seg.strip(), base + lead_ws(seg)))
            base += cut
            p = p[cut:]
        if p.strip():
            out.append((p.strip(), base + lead_ws(p)))
    return out


def pack_parts(text: str, max_chars: int) -> List[str]:
    """把过长的条文拆成若干段（embedding 有长度上限，超长会被**静默截断**）。
    优先在款项边界（1 / 2 / a) / ①）切，其次在句号切，避免拆碎句子。"""
    return [p for p, _ in pack_parts_with_offsets(text, max_chars)]


def load_standard_name(filename: str) -> str:
    """从文件名抽标准名称，如「建筑电气与智能化通用规范 GB 55024-2022」"""
    base = os.path.splitext(filename)[0]
    base = re.sub(r"^(国家标准|地方标准|行业标准)—", "", base)
    base = re.sub(r"【[^】]*】", "", base)
    return re.sub(r"[《》]", "", base).strip()


# ---------------------------------------------------------------- 逐页落盘
def collect_pages(out_dir: str) -> Dict[str, Dict]:
    p = os.path.join(out_dir, "pages.jsonl")
    done = {}
    if os.path.exists(p):
        with io.open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    done["%s:%d" % (r["file_idx"], r["page"])] = r
    return done


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default="all", help="all 或逗号分隔索引，如 4,13,15")
    ap.add_argument("--max-pages", type=int, default=0, help="每份最多处理页数（冒烟用）")
    ap.add_argument("--out", default=r"D:\rag_bench\kb")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--no-ocr", action="store_true", help="只走文本层，不 OCR")
    ap.add_argument("--max-chars", type=int, default=400,
                    help="单 chunk 目标上限；超长条文按款项/句号拆段（embedding 会截断超长输入）")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--chunk-only", action="store_true", help="跳过抽页，只从 pages.jsonl 重切分")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    pages_path = os.path.join(args.out, "pages.jsonl")
    log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "dpi": args.dpi,
           "files": args.files, "per_file": [], "errors": [],
           "rejects": {}}   # 按闸门拒收原因计数（D28）

    if not args.chunk_only:
        if not args.no_ocr and get_ocr(args.threads) is None:
            print("!! OCR 引擎不可用（%s）→ 扫描页将全部判 fail。" % _OCR_ERR, flush=True)
            print("!! 检查是否跑在项目 venv：D:\\Git_programs\\competitions\\.venv", flush=True)
        files = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
        idxs = list(range(len(files))) if args.files == "all" else [int(x) for x in args.files.split(",")]
        done = collect_pages(args.out) if args.resume else {}
        if not args.resume and os.path.exists(pages_path):
            os.remove(pages_path)
        mode = "a" if args.resume else "w"
        t_all = time.time()

        with io.open(pages_path, mode, encoding="utf-8") as fout:
            for idx in idxs:
                fp = os.path.join(PDF_DIR, files[idx])
                doc = pymupdf.open(fp)
                limit = min(doc.page_count, args.max_pages) if args.max_pages else doc.page_count
                stat = {"file_idx": idx, "file": files[idx], "pages": limit,
                        "text": 0, "ocr": 0, "blank": 0, "fail": 0, "toc": 0,
                        "repaired": 0, "ocr_sec": 0.0, "tables": 0, "fail_with_text": 0}

                for pno in range(limit):
                    if "%d:%d" % (idx, pno) in done:
                        continue
                    rec = {"file_idx": idx, "file": files[idx], "page": pno}
                    try:
                        has_table = page_has_table(doc[pno])
                        raw = doc[pno].get_text()
                        fixed, nfix = repair_lookalikes(normalize(raw))
                        fixed = strip_running_heads(fixed, has_table)
                        ok, diag = page_usable(fixed)
                        src = "text"
                        fail_diag = None   # 失败那一侧的诊断（文本层或 OCR 侧）
                        if not ok and not args.no_ocr:
                            pix, dark, std = render_gray(doc, pno, args.dpi)
                            if is_blank(dark, std):
                                src = "blank"  # 空白页/仅水印页：不 OCR
                            else:
                                otext, sec = ocr_pix(pix, "%d_%d" % (idx, pno), args.threads)
                                stat["ocr_sec"] += sec
                                if otext:
                                    t2 = strip_running_heads(normalize(otext), has_table)
                                    ok2, diag2 = page_usable(t2, min_cjk=10)
                                    if ok2:
                                        fixed, ok, diag, src = t2, True, diag2, "ocr"
                                    else:
                                        src, fail_diag = "fail", diag2   # 闸门拒收：留住 OCR 侧诊断
                                else:
                                    src = "fail"
                                    fail_diag = {"reason": "ocr_empty", "cjk": 0,
                                                 "common": 0.0, "suspect": 0.0}
                        if not ok and src != "blank":
                            src = "fail"
                            if fail_diag is None:
                                fail_diag = diag      # 文本层单路判死（含 --no-ocr）
                        # 丢弃「有大量中文但两条路都没过」的页时要出声 —— 静默丢数据是最危险的失败模式(D19)
                        # 修 D28：此处原读**文本层** diag，而拒收实际发生在 OCR 侧 → 告警永不触发。
                        if src == "fail":
                            fd = fail_diag
                            rk = str(fd.get("reason", "?"))
                            log["rejects"][rk] = log["rejects"].get(rk, 0) + 1
                            if max(fd.get("cjk", 0), diag.get("cjk", 0)) >= 50:
                                stat["fail_with_text"] += 1
                                print("  ! f%02d p%d DROPPED reason=%s ocr_cjk=%d text_cjk=%d"
                                      % (idx, pno, rk, fd.get("cjk", 0), diag.get("cjk", 0)),
                                      flush=True)
                        rec["blank"] = (src == "blank")
                        toc = ok and is_toc_page(fixed)
                        rec.update({
                            "source": src, "n_chars": len(fixed),
                            "cjk": diag.get("cjk", 0),
                            "common_ratio": round(diag.get("common", 0.0), 3),
                            "suspect": round(diag.get("suspect", 0.0), 4),
                            "repaired": nfix, "has_table": has_table,
                            "is_toc": toc,
                            # 空字符串 = 未拒收；非空 = 被哪条判据拒的（D28）
                            "reject_reason": (fail_diag.get("reason", "") if fail_diag else ""),
                            "text": fixed,
                        })
                        if toc:
                            stat["toc"] += 1
                        elif src == "text":
                            stat["text"] += 1
                        elif src == "ocr":
                            stat["ocr"] += 1
                        elif src == "blank":
                            stat["blank"] += 1
                        else:
                            stat["fail"] += 1
                        stat["repaired"] += nfix
                        if has_table:
                            stat["tables"] += 1
                    except Exception as e:
                        rec.update({"source": "error", "error": str(e), "text": ""})
                        stat["fail"] += 1
                        log["errors"].append({"file_idx": idx, "page": pno, "err": str(e)})

                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    if (pno + 1) % 10 == 0:
                        print("  f%02d %d/%d text=%d ocr=%d blank=%d fail=%d toc=%d ocrSec=%.0f" % (
                            idx, pno + 1, limit, stat["text"], stat["ocr"], stat["blank"],
                            stat["fail"], stat["toc"], stat["ocr_sec"]), flush=True)
                doc.close()
                log["per_file"].append(stat)
                print("FILE f%02d done pgs=%d text=%d ocr=%d blank=%d fail=%d toc=%d repairs=%d tables=%d ocrSec=%.0f" % (
                    idx, stat["pages"], stat["text"], stat["ocr"], stat["blank"], stat["fail"],
                    stat["toc"], stat["repaired"], stat["tables"], stat["ocr_sec"]), flush=True)
        log["elapsed_sec"] = round(time.time() - t_all, 1)

    # ---------------- 切分：先把每份文件的可用页拼回全文 ----------------
    recs = list(collect_pages(args.out).values())
    recs.sort(key=lambda r: (r["file_idx"], r["page"]))
    by_file: Dict[int, List[Dict]] = {}
    for r in recs:
        by_file.setdefault(r["file_idx"], []).append(r)

    chunks = []
    seen_ids = {}      # 见 uniq_id：同页同条款号会重复，id 必须唯一
    n_id_fixed = 0

    def uniq_id(base: str) -> str:
        # id = 文件+页+条款号。但**同页内条款号可能重复**（页眉、交叉引用、表格里的号），
        # 于是同一个 id 被产出 2~3 次 —— 实测 6 份里 55 处。
        # 后果：id 是评测的 gold 标签，重复会让 Recall 算成 1.05（>1 显然错）。
        # 这里给后来者加 #2/#3 后缀，保留可读 id 的同时保证唯一。
        nonlocal n_id_fixed
        n = seen_ids.get(base, 0) + 1
        seen_ids[base] = n
        if n == 1:
            return base
        n_id_fixed += 1
        return "%s#%d" % (base, n)

    for idx, rs in sorted(by_file.items()):
        std = load_standard_name(rs[0]["file"])
        # is_toc 在**切分时**判断而非抽页时 —— 原始文本留在 pages.jsonl，
        # 过滤规则改进后 `--chunk-only` 就能生效，不必重跑 5 小时 OCR。
        usable = [r for r in rs if r.get("source") in ("text", "ocr")
                  and r.get("text") and not is_toc_page(r["text"])]
        if not usable:
            continue
        # 拼接 + 页码偏移表
        parts, page_of_offset = [], []
        pos = 0
        for r in usable:
            page_of_offset.append((pos, r["page"]))
            parts.append(r["text"])
            pos += len(r["text"]) + 1
            parts.append("\n")
        full = "".join(parts)

        def page_at(off: int) -> int:
            lo = 0
            for p, pg in page_of_offset:
                if p <= off:
                    lo = pg
                else:
                    break
            return lo

        got_pages = set()  # 哪些页已由条文级 chunk 覆盖
        for u in split_clauses(full):
            body = u["body"].strip()
            # 弃无条文号的段：封面/目次/页眉残渣。D12 的目标是**可引用的条文**，
            # 没有条文号的段落引用不出「第几条」，属噪声。
            # 注意：**整页都没有条文号**的情况另走下面的「按页兜底」，不能整页丢（D26）。
            if not u["clause"]:
                continue
            if len(body) < 12:
                continue  # 空壳号头
            # 纯符号/纯数字的残句不要
            if sum(1 for c in body if is_cjk(c)) < 6:
                continue
            # 节标题自身不重复加前缀
            sec = u.get("section", "")
            head = sec if (sec and not sec.startswith(u["clause"])) else ""
            # 单元**起点**页：只用于 id 与 got_pages（刻意不改，见下方 part_pg 注释）
            pg = page_at(u["start"])
            # 过长条文拆段：否则 embedding 会静默截断，尾部内容检索不到
            parts_off = [(p, o) for p, o in pack_parts_with_offsets(body, args.max_chars)
                         if sum(1 for c in p if is_cjk(c)) >= 6]
            for pi, (part, part_off) in enumerate(parts_off):
                content = ("%s %s %s" % (head, u["clause"], part)).strip() if head else \
                          ("%s %s" % (u["clause"], part)).strip()
                suffix = "" if len(parts_off) == 1 else "_%d" % pi
                # D41：一个 clause 单元可能横跨多页（如 f05 附录 A 的表格被整段吞掉，
                # 113 个 part 却都继承单元起点页）⇒ 上报**该 part 自身所在页**。
                # 必须经 `body_off_to_full_off` 映射：body 丢了章/附录标题行，不是 full 的
                # 连续切片，`start + part_off` 会累积整页误差（见 split_clauses 的 segs 注释）。
                # id 仍用单元起点页 pg：id 内嵌页号（p%04d），改它会让 id 变化、
                # 使 197 条 gold 与 05 评测数字失联。id 是不透明键（检索/去重/引用都读
                # metadata），故保持 id 不动、只修 metadata。got_pages.add(pg) 同理不改，
                # 保证「按页兜底」产出的 chunk 集合逐字节不变。
                part_pg = page_at(body_off_to_full_off(u, part_off))
                part_is_ocr = any(r["source"] == "ocr" and r["page"] == part_pg for r in usable)
                part_has_tbl = any(r.get("has_table") and r["page"] == part_pg for r in usable)
                chunks.append({
                    "id": uniq_id("f%02d_p%04d_%s%s" % (
                        idx, pg, u["clause"].replace(".", "_"), suffix)),
                    "content": content,
                    "metadata": {
                        "file_idx": idx, "standard": std, "page": part_pg,
                        "clause": u["clause"], "chapter": u.get("chapter", ""),
                        "section": sec, "source": "ocr" if part_is_ocr else "text",
                        "has_table": part_has_tbl, "part": pi + 1, "n_parts": len(parts_off),
                        "n_chars": len(content), "page_level": False,
                    },
                })
                got_pages.add(pg)

        # 按页兜底（D26）：整页没有条文号的 —— 前言/引言、纯表格页、名单页。
        # 这些页在条文切分下产出 0 个 chunk，若不兜底就**整页静默消失**
        # （实测文本层 6 份里有 118 页 / 5.9 万字这样丢掉，占可用页内容的 ~23%）。
        # 保留可溯源：id 落到 `_pg`，metadata 标 page_level=True、clause=""。
        for r in usable:
            pg = r["page"]
            if pg in got_pages:
                continue
            txt = (r.get("text") or "").strip()
            if sum(1 for c in txt if is_cjk(c)) < 60 and len(txt) < 200:
                continue  # 太短，多半是封面/页眉
            parts = [p for p in pack_parts(txt, args.max_chars)
                     if sum(1 for c in p if is_cjk(c)) >= 6]
            for pi, part in enumerate(parts):
                suffix = "" if len(parts) == 1 else "_%d" % pi
                chunks.append({
                    "id": uniq_id("f%02d_p%04d_pg%s" % (idx, pg, suffix)),
                    "content": part,
                    "metadata": {
                        "file_idx": idx, "standard": std, "page": pg,
                        "clause": "", "chapter": "", "section": "",
                        "source": r.get("source", "text"),
                        "has_table": bool(r.get("has_table")),
                        "part": pi + 1, "n_parts": len(parts),
                        "n_chars": len(part), "page_level": True,
                    },
                })

    cp = os.path.join(args.out, "chunks.jsonl")
    with io.open(cp, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    log["n_pages"] = len(recs)
    log["n_chunks"] = len(chunks)
    log["n_dup_id_fixed"] = n_id_fixed   # 同页重复条款号被加后缀的次数
    sizes = sorted(len(c["content"]) for c in chunks)
    if sizes:
        log["chunk_chars"] = {"min": sizes[0], "median": sizes[len(sizes) // 2],
                              "max": sizes[-1], "mean": round(sum(sizes) / len(sizes), 1)}
    with io.open(os.path.join(args.out, "ingest_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print("\nPAGES %d  CHUNKS %d  DUP_ID_FIXED %d" % (
        len(recs), len(chunks), n_id_fixed), flush=True)
    if sizes:
        print("CHUNK_CHARS min=%d median=%d max=%d mean=%.1f" % (
            sizes[0], sizes[len(sizes) // 2], sizes[-1], sum(sizes) / len(sizes)), flush=True)
    print("OUT %s" % cp, flush=True)
    if log["rejects"]:
        print("REJECTS %s" % json.dumps(log["rejects"], ensure_ascii=False,
                                         sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
