# 后端接口对接配置说明

## ✅ 配置已完成

### 1. Vite 代理配置
**文件**: `client/vite.config.ts`

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:3000',  // FastAPI 默认端口
      changeOrigin: true
    }
  }
}
```

**说明**: 
- 前端请求 `http://localhost:8080/api/xxx` 会自动代理到 `http://localhost:3000/api/xxx`
- 无需修改后端端口，FastAPI 默认运行在 3000 端口

### 2. 后端接口列表

后端已实现以下接口（所有路由都带有 `/api` 前缀）：

#### 统计分析 - `/api/statistics`
- `GET /summary` - 时段汇总统计
  - 参数：`building_id`, `start_date`, `end_date`, `group_by`
  - 响应：`{ building_id, period, details[], summary: { total_elec, avg_elec } }`

- `GET /anomaly` - 异常检测
  - 参数：`building_id`, `start_date`, `end_date`, `threshold`
  - 响应：`{ building_id, period, total_points, anomaly_count, anomalies[] }`

#### 图表数据 - `/api/charts`
- `GET /trend` - 趋势图数据
  - 参数：`building_id`, `days`
  - 响应：`{ code: 200, data: { categories[], series[] } }`

- `GET /distribution` - 分布数据
  - 参数：`building_id`, `date`
  - 响应：`{ code: 200, data: { categories[], series[] } }`

#### 数据查询 - `/api/query`
- `GET /raw` - 原始能耗数据
  - 参数：`building_id`, `start_date`, `end_date`, `limit`, `offset`
  - 响应：`{ code: 200, data[], pagination: { total, limit, offset, has_more } }`

#### 智能问答 - `/api/chat`
- `POST /ask` - 智能问答
  - Body: `{ query, building_id, session_id }`
  - 响应：`{ answer, type, sources[], data[] }`

#### 报表导出 - `/api/export`
- `GET /excel` - 导出 Excel
  - 参数：`building_id`, `start_date`, `end_date`
  - 响应：二进制文件流

- `GET /csv` - 导出 CSV
- `GET /pdf` - 导出 PDF

### 3. 前端 API 适配

已更新以下 API 文件以匹配后端实际接口：

#### `client/src/api/dashboard.ts`
```typescript
// KPI 数据
export const getKPIData = () => {
  return http.get('/statistics/summary', {
    params: {
      building_id: 'B001',
      start_date: today,
      end_date: today,
      group_by: 'day'
    }
  })
}

// 图表数据
export const getChartData = () => {
  return http.get('/charts/distribution', {
    params: { building_id: 'B001', date: today }
  })
}

// 趋势数据
export const getTrendData = () => {
  return http.get('/charts/trend', {
    params: { building_id: 'B001', days: 7 }
  })
}

// 异常列表
export const getAnomalyList = (limit = 5) => {
  return http.get('/statistics/anomaly', {
    params: {
      building_id: 'B001',
      start_date: today,
      end_date: today,
      threshold: 2.0
    }
  })
}
```

#### `client/src/api/analysis.ts`
```typescript
// 自然语言查询
export const parseNaturalQuery = (params) => {
  return http.post('/chat/ask', {
    query: params.query,
    building_id: params.context?.building_id || 'B001'
  })
}

// 数据查询
export const queryData = (params) => {
  return http.get('/query/raw', {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0],
      limit: params.pageSize,
      offset: (params.pageNum - 1)
    }
  })
}

// 统计摘要
export const getStatisticsSummary = (params) => {
  return http.get('/statistics/summary', {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    }
  })
}

// 异常统计
export const getAnomalyCount = (params) => {
  return http.get('/statistics/anomaly', {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    }
  })
}

// 导出报表
export const exportReport = (params) => {
  return http.get(`/export/${params.format}`, {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}
```

### 4. 类型定义更新

已更新以下类型文件以匹配后端实际响应格式：

- `client/src/types/dashboard.ts` - 仪表盘类型
- `client/src/types/analysis.ts` - 分析查询类型

### 5. 启动步骤

#### 启动后端（FastAPI）
```bash
cd server/A08
# 创建虚拟环境（如果还没有）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问后端文档：http://localhost:3000/docs

#### 启动前端
```bash
cd client
npm run dev
```

访问前端：http://localhost:8080

### 6. 数据流示例

#### Overview 页面加载流程
1. 前端调用 `GET /api/statistics/summary?building_id=B001&start_date=2024-01-01&end_date=2024-01-01`
2. FastAPI 返回：`{ building_id: "B001", summary: { total_elec: 1256.8, avg_elec: 52.37 } }`
3. 前端提取 `summary.total_elec` 显示为 KPI 卡片

#### Analysis 页面查询流程
1. 用户选择建筑和时间范围
2. 前端调用 `GET /api/query/raw?building_id=B001&start_date=2024-01-01&end_date=2024-01-01`
3. FastAPI 返回：`{ code: 200, data: [{ timestamp, electricity, is_anomaly }], pagination: {...} }`
4. 前端渲染表格和图表

### 7. 注意事项

#### 后端响应格式
后端所有接口统一返回格式：
```json
{
  "code": 200,  // 可选，部分接口没有此字段
  "data": { ... }  // 实际业务数据
}
```

#### 前端数据访问
- 部分接口返回 `response.data.data`（两层 data）
- 部分接口返回 `response.data`（一层 data）
- 需要根据具体接口调整访问路径

#### 参数格式转换
- 前端时间戳 → 后端日期字符串：`new Date(timestamp).toISOString().split('T')[0]`
- 前端建筑数组 → 后端单个建筑 ID：`params.buildings[0]`

### 8. 待优化项

1. **建筑名称关联** - 后端 `/query/raw` 返回的是 `building_id`，需要关联 `buildings` 表获取名称
2. **KPI 数据补充** - 后端 `/statistics/summary` 未提供 `energyChange`、`deviceOnlineRate` 等字段
3. **NL2Query 结构化** - 后端 `/chat/ask` 返回的是文本答案，需要改为结构化数据

### 9. 测试验证

#### 测试后端接口
```bash
# 测试统计接口
curl http://localhost:3000/api/statistics/summary?building_id=B001&start_date=2024-01-01&end_date=2024-01-01

# 测试图表接口
curl http://localhost:3000/api/charts/trend?building_id=B001&days=7
```

#### 测试前端
1. 访问 http://localhost:8080
2. 打开浏览器开发者工具 → Network
3. 查看 `/api/` 请求是否成功代理到 8000 端口
4. 检查响应数据是否正确解析

## 🎉 配置完成！

现在前端已完全适配后端实际接口，只需启动后端服务（8000 端口）即可正常联调。
