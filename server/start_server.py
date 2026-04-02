# start_server.py - 后端服务启动脚本
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# 设置项目根目录为当前目录的父目录
ROOT_DIR = Path(__file__).parent.absolute()
os.chdir(ROOT_DIR)

# 加载环境变量
load_dotenv()

# 设置 PYTHONPATH
import sys
sys.path.insert(0, str(ROOT_DIR))

# 配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 3000))

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "energy_management")
DB_USER = os.getenv("DB_USER", "root")

# TiDB Cloud 检测
IS_TIDB_CLOUD = "tidbcloud.com" in DB_HOST.lower()

# Render 部署检测
IS_RENDER = os.getenv("RENDER", False)
if IS_RENDER:
    PORT = int(os.getenv("PORT", 10000))
    print(f"[OK] Render 环境检测成功")
    print(f"[OK] 端口：{PORT}")

print(f"\n{'='*50}")
print(f"[START] 正在启动服务器...")
print(f"[INFO] 地址：http://localhost:{PORT}")

if IS_TIDB_CLOUD:
    print(f"[INFO] 数据库：TiDB Cloud (远程)")
else:
    print(f"[INFO] 数据库：{DB_HOST}:{DB_PORT}")

print(f"{'='*50}\n")

# 启动应用
if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=False,  # Render 生产环境关闭热重载
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[INFO] 服务器已关闭")
    except Exception as e:
        print(f"\n[ERROR] 启动失败：{str(e)}")
