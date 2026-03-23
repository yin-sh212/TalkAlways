# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from app.config import config
from app.database.db import Database

# 导入所有路由模块
from app.api import query_api
from app.api import statistics_api
from app.api import chart_api
from app.api import chat_api
from app.api import mcp_api
from app.api import export_api  # 新增：导入报表导出模块
from app.api import upload_api
from app.api import auth_api
from app.api import alarm_api
from app.api import device_api
from app.api import energy_api
from app.api import knowledge_api
from app.api import analysis_api  # 新增：导入能耗分析模块

from datetime import datetime
import os

PORT = int(os.getenv("PORT", 3000))
HOST = os.getenv("HOST", "0.0.0.0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    await Database.get_pool()
    print(f"✅ {config.APP_NAME} v{config.APP_VERSION} 启动成功")
    print(f"📚 接口文档: http://localhost:{PORT}/docs")
    print(f"🔑 登录页面: http://localhost:{PORT}/static/login_final.html")
    print(f"💬 聊天页面: http://localhost:{PORT}/static/chat.html")

    yield  # 这里会暂停，应用运行期间会保持

    # 关闭时执行
    await Database.close_pool()
    print("👋 应用已关闭")

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    debug=config.DEBUG,
    lifespan=lifespan
)

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

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
app.include_router(query_api.router)
app.include_router(statistics_api.router)
app.include_router(chart_api.router)
app.include_router(chat_api.router)
app.include_router(mcp_api.router)
app.include_router(export_api.router)  # 新增：注册报表导出路由
app.include_router(upload_api.router)
app.include_router(auth_api.router)
app.include_router(alarm_api.router)  # 新增：注册告警管理路由
app.include_router(device_api.router)
app.include_router(energy_api.router)
app.include_router(knowledge_api.router)
app.include_router(analysis_api.router)  # 新增：注册能耗分析路由


@app.get("/")
async def root():
    """根路径"""
    return {
        "app_name": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    try:
        # 测试数据库连接
        await Database.fetch_one("SELECT 1 as health")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

# app/main.py 文件末尾添加
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, reload=True)