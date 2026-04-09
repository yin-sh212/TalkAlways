# start_server.py - 后端服务启动脚本
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# 设置工作目录为 server 文件夹（确保相对路径正确）
server_dir = Path(__file__).parent
os.chdir(server_dir)

# 加载环境变量
load_dotenv()

# 读取 Render 自动分配的端口（这是唯一正确写法）
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 3000))  # 必须用 os.environ.get

# ==============================================
# 🔥 关键修复：关闭所有不必要的日志，减少内存占用
# ==============================================
import logging
logging.basicConfig(level=logging.WARNING)

print(f"[OK] 服务器启动中...")
print(f"[OK] 监听地址：{HOST}:{PORT}")

# 启动应用
if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=False,
            log_level="warning",  # 降低日志，减少内存
            workers=1  # 免费版只能用 1 个进程
        )
    except Exception as e:
        print(f"[ERROR] 启动失败：{str(e)}")