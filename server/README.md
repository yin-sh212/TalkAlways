# Server 项目结构

## 📁 目录说明

```
server/
├── app/                    # 主应用目录
│   ├── api/               # API 路由模块
│   │   ├── query_api.py      # 查询接口
│   │   ├── statistics_api.py # 统计接口
│   │   ├── chart_api.py      # 图表接口
│   │   ├── chat_api.py       # 聊天接口
│   │   ├── mcp_api.py        # MCP 接口
│   │   └── export_api.py     # 报表导出接口
│   ├── auth/              # 认证模块（可选）
│   ├── database/          # 数据库相关
│   │   ├── db.py          # 数据库连接
│   │   └── models.py      # 数据模型
│   ├── services/          # 业务逻辑层
│   ├── util/              # 工具函数
│   ├── config.py          # 配置文件
│   ├── init.py           # 初始化文件
│   └── main.py           # FastAPI 主应用入口
├── data/                  # 数据文件目录（可选）
├── static/                # 静态资源目录
├── .env                   # 环境变量配置
├── requirements.txt       # Python 依赖
├── check_fonts.py        # 字体检查脚本
└── test_*.py             # 测试脚本
```

## 🚀 快速开始

### 1. 安装依赖
```bash
cd server
pip install -r requirements.txt
```

### 2. 配置环境变量
编辑 `.env` 文件，设置数据库连接等配置：
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=energy_management
```

### 3. 运行服务
```bash
# 方式一：直接运行
python app/main.py

# 方式二：使用 uvicorn（推荐）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**默认运行端口**: http://localhost:8000

## 📋 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 项目结构变更说明

**注意**: 本项目已取消 A08 子模块嵌套结构，所有文件直接放置在 server 目录下。

原结构：
```
server/
└── A08/
    ├── app/
    ├── data/
    └── ...
```

新结构：
```
server/
├── app/
├── data/
└── ...
```

## 📝 主要模块

### API 路由 (app/api/)
- **query_api.py**: 数据查询接口
- **statistics_api.py**: 统计数据接口
- **chart_api.py**: 图表数据接口
- **chat_api.py**: 智能对话接口
- **mcp_api.py**: MCP 相关接口
- **export_api.py**: 报表导出接口

### 数据库 (app/database/)
- **db.py**: 数据库连接管理
- **models.py**: ORM 模型定义

### 业务服务 (app/services/)
- 各类业务逻辑实现

## ⚠️ 注意事项

1. 确保 MySQL 数据库已启动并正确配置
2. 首次运行前需要安装所有依赖
3. 生产环境请修改 `.env` 中的默认密码
4. 定期清理 `__pycache__` 缓存文件
