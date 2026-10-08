from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from starlette.concurrency import run_in_threadpool
from app.config import config
from app.database.db import Database
from app.services import rag_answer

# 导入所有路由模块
from app.api import query_api
from app.api import statistics_api
from app.api import chart_api
from app.api import chat_api
from app.api import mcp_api
from app.api import export_api
from app.api import upload_api
from app.api import auth_api
from app.api import alarm_api
from app.api import device_api
from app.api import knowledge_api
from app.api import analysis_api
from app.api import realtime_api
from app.api import ai_analyst
from app.api import chart_analysis
from app.api import floor_api
from app.api import space_api
from app.api import meter_binding_api
from app.api import space_energy_api

from datetime import datetime
import os

PORT = int(os.getenv("PORT", 3000))
HOST = os.getenv("HOST", "0.0.0.0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await Database.fetch_one("SELECT 1 as test")
        print("数据库连接成功")
    except Exception as e:
        print(f"数据库连接失败：{e}")

    # 预热 hybrid RAG 索引 + 两个模型（embedding / reranker）。
    # 首次启动 data/hybrid_index 不存在，要现场构建（几分钟）；之后只加载。
    # 整段 try/except：预热失败绝不能拖垮整个应用 —— 请求进来时
    # get_retriever() 还会懒加载兜底一次。
    if config.RAG_ENABLED:
        try:
            await run_in_threadpool(rag_answer.warmup)
            print("RAG 索引与模型预热完成")
        except Exception as e:
            print(f"⚠️ RAG 预热失败（问答将走懒加载或降级普通 LLM）：{e}")

    print(f"{config.APP_NAME} v{config.APP_VERSION} 启动成功")
    yield

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    debug=config.DEBUG,
    lifespan=lifespan
)

# ======================================
# 第二步：立即配置 CORS！！（必须放在注册路由前面）
# ======================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://competitions-shenghui-yins-projects.vercel.app",
        "*"  # 临时全开，确保能连上
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================
# 第三步：自定义接口文档
# ======================================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="建筑能源管理系统 API",
        version="1.0.0",
        description=(
            "# 🏢 建筑能源智能管理系统\n\n"
            "## 项目简介\n"
            "基于 FastAPI + MySQL 的建筑能源管理系统，提供数据查询、统计分析、智能问答等功能。\n\n"
            "## 核心功能\n"
            "- 📊 **数据查询**：多条件查询能耗数据\n"
            "- 📈 **统计分析**：时段汇总、COP计算、异常检测\n"
            "- 🤖 **智能问答**：基于RAG的运维知识问答\n"
            "- 📑 **报表导出**：CSV/Excel/PDF格式导出\n"
            "- 🔐 **用户认证**：手机号/邮箱登录\n\n"
            "## 技术栈\n"
            "- FastAPI + MySQL\n"
            "- LangChain + FAISS (RAG)\n"
            "- JWT 用户认证"
        ),
        routes=app.routes,
    )

    # 添加中文标签
    tag_descriptions = {
        "数据查询": "查询建筑、设备、能耗数据",
        "统计分析": "能耗统计、COP计算、异常检测",
        "图表数据": "为前端提供ECharts格式数据",
        "智能问答": "RAG智能问答接口",
        "MCP协议": "Model Context Protocol 接口",
        "报表导出": "CSV/Excel/PDF格式导出",
        "数据管理": "数据上传和模板下载",
        "认证": "用户登录、注册、信息查询",
    }

    for tag in openapi_schema.get("tags", []):
        if tag["name"] in tag_descriptions:
            tag["description"] = tag_descriptions[tag["name"]]

    # 翻译路径描述
    for path, methods in openapi_schema["paths"].items():
        for method, detail in methods.items():
            if "summary" in detail:
                # 自动翻译摘要（可以用AI，这里先手动映射）
                summary_map = {
                    "Get Raw Data": "获取原始能耗数据",
                    "Get Buildings": "获取建筑列表",
                    "Get Meters": "获取监测点列表",
                    "Get Device Status": "获取设备状态",
                    "Get Summary": "获取时段汇总",
                    "Calculate Cop": "计算能效比(COP)",
                    "Detect Anomaly": "检测能耗异常",
                    "Get Trend Data": "获取趋势图数据",
                    "Get Comparison Data": "获取对比图数据",
                    "Get Distribution Data": "获取分布图数据",
                    "Ask Question": "智能问答",
                    "Chat Health": "问答服务健康检查",
                    "Mcp Chat": "MCP协议聊天",
                    "List Tools": "列出MCP工具",
                    "Export Csv": "导出CSV",
                    "Export Excel": "导出Excel",
                    "Export Pdf": "导出PDF",
                    "Upload Csv": "上传CSV文件",
                    "Download Template": "下载CSV模板",
                    "Login": "用户登录",
                    "Logout": "退出登录",
                    "Get Current User": "获取当前用户信息",
                    "Register": "用户注册",
                    "Health Check": "健康检查",
                }
                if detail["summary"] in summary_map:
                    detail["summary"] = summary_map[detail["summary"]]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ======================================
# 第四步：最后才注册路由！！
# ======================================
app.include_router(query_api.router)
app.include_router(statistics_api.router)
app.include_router(chart_api.router)
app.include_router(chat_api.router)
app.include_router(mcp_api.router)
app.include_router(export_api.router)
app.include_router(upload_api.router)
app.include_router(auth_api.router)
app.include_router(alarm_api.router)
app.include_router(device_api.router)
app.include_router(knowledge_api.router)
app.include_router(analysis_api.router)
app.include_router(realtime_api.router)
app.include_router(ai_analyst.router)
app.include_router(chart_analysis.router)
app.include_router(floor_api.router)
app.include_router(space_api.router)
app.include_router(meter_binding_api.router)
app.include_router(space_energy_api.router)

# ======================================
# 接口
# ======================================
@app.get("/")
async def root():
    return {
        "app_name": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    try:
        await Database.fetch_one("SELECT 1 as health")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

# ======================================
# 启动
# ======================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
