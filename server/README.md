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
├── test_*.py             # 测试脚本
├── README.md             # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖
```bash
cd server
python -m pip install -r requirements.txt
```

**注意**: Python 3.13 用户请查看 [安装指南](INSTALLATION.md) 了解兼容性处理。

### 2. 配置环境变量
编辑 `.env` 文件，设置数据库连接等配置：
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=ysh212119
DB_NAME=energy_management
APP_NAME=建筑能源管理系统
APP_VERSION=1.0.0
DEBUG=True
```

### 3. 运行服务

**方式一：使用 uvicorn（推荐）**
```bash
# 开发环境（开启热重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 3000

# 生产环境（关闭热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

**方式二：直接运行**
```bash
python -m app.main
```

**默认运行端口**: http://localhost:3000

### 4. 前端配置
确保前端的 `vite.config.ts` 代理配置指向正确的后端端口：
```ts
proxy: {
  '/api': {
    target: 'http://localhost:3000',  // 确保端口为 3000
    changeOrigin: true
  }
}
```

## 📋 API 文档

### 在线文档
启动服务后访问：
- **Swagger UI**: http://localhost:3000/docs (交互式测试)
- **ReDoc**: http://localhost:3000/redoc (美观文档)

### 离线文档
查看 [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) 文件，包含：
- ✅ 所有接口的详细说明
- ✅ 每个接口都有中文描述
- ✅ 完整的请求参数说明
- ✅ 响应格式示例
- ✅ curl 使用示例

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
- **query_api.py**: 数据查询接口（原始数据、建筑列表、监测点、设备状态）
- **statistics_api.py**: 统计数据接口（时段汇总、COP 计算、异常检测）
- **chart_api.py**: 图表数据接口（趋势图、对比图、分布图）
- **chat_api.py**: 智能对话接口（RAG 问答系统）
- **mcp_api.py**: MCP 协议接口（工具调用）
- **export_api.py**: 报表导出接口（CSV、Excel、PDF）

### 数据库 (app/database/)
- **db.py**: 数据库连接管理（连接池、异步查询）
- **models.py**: ORM 模型定义

### 业务服务 (app/services/)
- **anomaly_detector.py**: 异常检测算法（3σ原则）
- **rag_service.py**: RAG 智能问答服务

## ⚠️ 注意事项

1. 确保 MySQL 数据库已启动并正确配置
2. 首次运行前需要安装所有依赖
3. 生产环境请修改 `.env` 中的默认密码
4. 定期清理 `__pycache__` 缓存文件

## 🎯 常用接口速查

### 查询建筑列表
```bash
curl "http://localhost:3000/api/query/buildings"
```

### 获取近 7 天趋势
```bash
curl "http://localhost:3000/api/charts/trend?building_id=B001&days=7"
```

### 智能问答
```bash
curl -X POST "http://localhost:3000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "B001 建筑昨天用电量是多少？"}'
```

### 导出 Excel 报表
```bash
curl "http://localhost:3000/api/export/excel?building_id=B001&start_date=2024-03-01&end_date=2024-03-07" \
  --output report.xlsx
```

## 📚 相关文档

- [API 完整文档](API_DOCUMENTATION.md) - 所有接口的详细说明和示例
- [项目结构调整](../REFACTOR_SUMMARY.md) - A08 取消说明
- [主题切换功能](src/utils/README_Theme_Switch.md) - 前端主题配置
