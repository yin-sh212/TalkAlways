import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 离线加载模型：本机访问不了 HuggingFace，设了才能让错误的模型路径「快速失败」，
# 而不是每次尝试都卡 ~30s 在 DNS 上。要在线下载模型就在 .env 里设 HF_HUB_OFFLINE=0。
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Windows 中文控制台/重定向的默认编码是 GBK，打印 emoji（✅/⚠️/❌）会抛
# UnicodeEncodeError 而不是输出 —— 非流式问答成功路径的 print("✅ ...") 因此让
# /api/chat/ask 恒定 500（2026-09-28 端到端验证时发现）。这里只改「编不出来怎么办」：
# 中文照常（GBK 能编码），编不出的字符退化成 '?'，绝不因一行日志把业务打挂。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        # 非 TextIOWrapper（pytest 捕获、已被替换的流）时无此方法，跳过即可
        pass


class Config:
    # 数据库配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
    DB_NAME = os.getenv("DB_NAME", "energy_management")

    # 数据库连接 URL
    DATABASE_URL = f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # 应用配置
    APP_NAME = os.getenv("APP_NAME", "建筑能源管理系统")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # ===== 「无效回答」判定（原为两处硬编码，现集中为一份配置）=====
    # 某些回答会成段复述演示/公司介绍（与用户问题无关），需要判为无效并走降级链。
    # 命中规则：回答长度 > MIN_LEN 且包含任一 MARKER。改词表不用改代码。
    INVALID_ANSWER_MARKERS = [
        m for m in os.getenv("INVALID_ANSWER_MARKERS", "中建八局二建,擎翼数字中枢").split(",") if m
    ]
    INVALID_ANSWER_MIN_LEN = int(os.getenv("INVALID_ANSWER_MIN_LEN", "300"))

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "60"))

    # ===== 混合检索 RAG（默认值 = 全量 394 问端到端评测最优配置）=====
    # 评测结论见 task6_RAG/05_§7.2：主杠杆是池深（P 20→50），权重仅次要。
    RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in ("1", "true", "yes")  # 线上开关
    RAG_MODE = os.getenv("RAG_MODE", "hybrid_rerank")
    RAG_POOL = int(os.getenv("RAG_POOL", "50"))          # 调小到 20 可省约 2.5× 重排耗时
    RAG_RRF_K = int(os.getenv("RAG_RRF_K", "5"))
    RAG_W_BM25 = float(os.getenv("RAG_W_BM25", "2.0"))
    RAG_W_VECTOR = float(os.getenv("RAG_W_VECTOR", "1.0"))
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))         # 喂给 LLM 的片段数
    RAG_MIN_HITS = int(os.getenv("RAG_MIN_HITS", "1"))   # 命中少于这么多条就降级为普通 LLM
    # 重排分阈值门（B1）：top-1 rerank_score 低于它就判为「没检索到相关内容」→ 降级。
    # 0.0 = 关闭（保持接线时的行为）。标定见 task6_RAG/02 D45。
    RAG_MIN_RERANK = float(os.getenv("RAG_MIN_RERANK", "0.0"))
    # 在线近重复折叠（D41）：同一「失控条款单元」的兄弟段近重复且共享前缀，
    # 会让一次检索的 5 条命中大半同源。超采后按字符 3-gram Jaccard 折叠再截断。
    RAG_DEDUP_FETCH = int(os.getenv("RAG_DEDUP_FETCH", "15"))       # 超采条数（≥ RAG_TOP_K）
    RAG_DEDUP_JACCARD = float(os.getenv("RAG_DEDUP_JACCARD", "0.85"))  # ≥ 此值视为重复
    RAG_CHUNKS_PATH = os.getenv("RAG_CHUNKS_PATH", "./data/kb/chunks.jsonl")
    RAG_INDEX_DIR = os.getenv("RAG_INDEX_DIR", "./data/hybrid_index")
    RAG_EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "shibing624/text2vec-base-chinese")
    # 必须是本地目录：离线环境下传 HF 仓库名（BAAI/bge-reranker-base）会直接失败
    RAG_RERANK_MODEL = os.getenv("RAG_RERANK_MODEL", "D:/models/bge-reranker-base")


config = Config()
