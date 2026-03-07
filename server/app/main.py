# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import config
from app.database.db import Database

# 导入所有路由模块
from app.api import query_api
from app.api import statistics_api
from app.api import chart_api
from app.api import chat_api
from app.api import mcp_api
from app.api import export_api  # 新增：导入报表导出模块

from datetime import datetime

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    debug=config.DEBUG
)

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

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库连接池"""
    await Database.get_pool()
    print(f"[OK] {config.APP_NAME} v{config.APP_VERSION} started")
    print(f"[INFO] API docs: http://localhost:3000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭数据库连接池"""
    await Database.close_pool()
    print("[BYE] App closed")


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