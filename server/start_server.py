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

# 数据库配置信息（用于调试）
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "energy_management")
DB_USER = os.getenv("DB_USER", "root")

print(f"🚀 正在启动服务器...")
print(f"📍 主机：{HOST}:{PORT}")
print(f"📚 接口文档：http://localhost:{PORT}/docs")
print(f"🔑 登录页面：http://localhost:{PORT}/static/login_final.html")
print(f"💬 聊天页面：http://localhost:{PORT}/static/chat.html")
print("=" * 50)
print(f"📦 数据库配置:")
print(f"   - Host: {DB_HOST}:{DB_PORT}")
print(f"   - Database: {DB_NAME}")
print(f"   - User: {DB_USER}")
if DB_HOST == "localhost":
    print(f"   ✅ 使用本地数据库")
else:
    print(f"   ⚠️  使用远程数据库：{DB_HOST}")
print("=" * 50)

# 启动应用
if __name__ == "__main__":
    try:
        print("⏳ 正在连接数据库...")
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 检测到退出信号，正在关闭服务器...")
    except Exception as e:
        print(f"\n❌ 服务器启动失败：{str(e)}")
        print("\n💡 请检查:")
        print("   1. .env 文件中的数据库配置是否正确")
        print("   2. MySQL 服务是否已启动")
        print("   3. 端口是否被占用 (3000)")
        print("   4. 数据库用户权限是否正确")
        print("\n🔧 快速排查命令:")
        print("   - 测试数据库连接：mysql -u root -p")
        print("   - 查看端口占用：netstat -ano | findstr :3000")
