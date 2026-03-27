# 9 月数据集流式推送功能

## 📌 功能简介

本项目新增了 9 月能耗数据集的流式推送功能，采用 SSE (Server-Sent Events) 技术实现大数据量的实时传输。

## 🚀 快速开始

### 1. 启动后端服务

```bash
cd server
python start_server.py
```

服务将运行在 `http://localhost:3000`

### 2. 启动前端服务

```bash
cd client
npm install
npm run dev
```

前端将运行在 `http://localhost:8080`

### 3. 访问功能页面

打开浏览器访问：`http://localhost:8080/#/september-data`

## 📡 API 接口

### 流式推送接口

```http
GET /api/export/september/stream
参数:
- building_id: 可选，建筑编号
- year: 可选，年份，默认 2016
- batch_size: 可选，每批条数，默认 100，范围 10-1000
```

### 分页查询接口

```http
GET /api/export/september/batch
参数:
- building_id: 可选，建筑编号
- year: 可选，年份，默认 2016
- page: 可选，页码，默认 1
- page_size: 可选，每页大小，默认 100
```

## 🧪 测试方法

### 使用测试脚本

```bash
cd server
python test_september_stream.py
```

### 使用 curl

```bash
# 测试流式接口
curl -N "http://localhost:3000/api/export/september/stream?year=2016&batch_size=10"

# 测试分页接口
curl "http://localhost:3000/api/export/september/batch?year=2016&page=1&page_size=10"
```

## 📁 相关文件

### 后端
- `server/app/api/export_api.py` - API 实现
- `server/test_september_stream.py` - 测试脚本

### 前端
- `client/src/api/export.ts` - API 调用封装
- `client/src/views/SeptemberData.vue` - 示例页面
- `client/src/router/index.ts` - 路由配置

## 📖 详细文档

完整的使用文档、API 说明和示例代码请参考项目记忆库中的相关文档。

## ⚙️ 核心特性

✅ **流式推送** - 基于 SSE 的实时数据传输  
✅ **分批处理** - 避免内存溢出，支持大数据量  
✅ **进度反馈** - 实时显示推送进度  
✅ **灵活配置** - 支持按建筑、年份、批次大小筛选  
✅ **双模式** - 同时支持流式和分页两种查询方式  

## 🛠️ 技术栈

- **后端**: FastAPI + Python + MySQL/TiDB
- **前端**: Vue 3 + TypeScript + Ant Design Vue
- **通信协议**: SSE (Server-Sent Events)

## 📝 更新日志

### v1.0.0 (2026-03-27)
- ✅ 实现 9 月数据集流式推送 API
- ✅ 实现分页查询 API
- ✅ 创建前端调用函数
- ✅ 创建示例 Vue 组件
- ✅ 添加路由配置
- ✅ 编写测试脚本和使用文档

---

**开发时间**: 2026-03-27  
**版本**: v1.0.0  
**状态**: ✅ 已完成
