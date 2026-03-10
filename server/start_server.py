# start_server.py - 后端服务启动脚本
import uvicorn
import os
from pathlib import Path

# 设置项目根目录为当前目录的父目录
ROOT_DIR = Path(__file__).parent.absolute()
os.chdir(ROOT_DIR)

# 设置PYTHONPATH
import sys
sys.path.insert(0, str(ROOT_DIR))

# 配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 3000))

print(f"🚀 正在启动服务器...")
print(f"📍 主机：{HOST}:{PORT}")
print(f"📚 接口文档：http://localhost:{PORT}/docs")
print(f"🔑 登录页面：http://localhost:{PORT}/static/login_final.html")
print(f"💬 聊天页面：http://localhost:{PORT}/static/chat.html")
print("=" * 50)

# 启动应用
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )
