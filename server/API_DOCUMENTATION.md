# 智慧能源管理系统 - 后端 API 文档

## 📋 文档说明

本文档提供了完整的后端 API 接口说明，每个接口都包含：
- **功能描述**：接口的用途
- **请求参数**：参数类型和说明
- **响应格式**：返回数据结构
- **使用示例**：实际的请求和响应示例

**基础地址**: `http://localhost:3000`  
**API 文档**: `http://localhost:3000/docs` (Swagger UI)  
**ReDoc**: `http://localhost:3000/redoc`

---

## 🔐 1. 数据查询 API (`/api/query`)

### 1.1 获取原始能耗数据

**接口**: `GET /api/query/raw`

**功能**: 获取原始能耗数据，支持多条件筛选和分页

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| building_id | string | 否 | - | 建筑编号 |
| meter_id | string | 否 | - | 监测点编号 |
| start_date | string | 否 | - | 开始日期 (YYYY-MM-DD) |
| end_date | string | 否 | - | 结束日期 (YYYY-MM-DD) |
| limit | integer | 否 | 100 | 每页数量 (1-1000) |
| offset | integer | 否 | 0 | 偏移量 |

**响应示例**:
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "building_id": "B001",
      "meter_id": "M001",
      "timestamp": "2024-03-07 10:00:00",
      "electricity": 125.6,
      "water": 2.3,
      "ambient_temp": 25.5,
      "is_anomaly": 0
    }
  ],
  "pagination": {
    "total": 1000,
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

**使用示例**:
```bash
# 查询 B001 建筑最近 100 条数据
curl "http://localhost:3000/api/query/raw?building_id=B001&limit=100"

# 查询指定日期范围的数据
curl "http://localhost:3000/api/query/raw?building_id=B001&start_date=2024-03-01&end_date=2024-03-07"
```

---

### 1.2 获取建筑列表

**接口**: `GET /api/query/buildings`

**功能**: 获取所有建筑信息

**请求参数**: 无

**响应示例**:
```json
{
  "code": 200,
  "data": [
    {
      "id": "B001",
      "name": "行政楼",
      "type": "办公",
      "area": 5000.0
    },
    {
      "id": "B002",
      "name": "实验楼",
      "type": "科研",
      "area": 8000.0
    }
  ]
}
```

**使用示例**:
```bash
curl "http://localhost:3000/api/query/buildings"
```

---

### 1.3 获取监测点列表

**接口**: `GET /api/query/meters`

**功能**: 获取监测点设备列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 否 | 建筑编号（筛选特定建筑） |

**响应示例**:
```json
{
  "code": 200,
  "data": [
    {
      "id": "M001",
      "building_id": "B001",
      "type": "电表",
      "location": "1 层配电室",
      "status": "normal"
    }
  ]
}
```

**使用示例**:
```bash
# 获取所有监测点
curl "http://localhost:3000/api/query/meters"

# 获取 B001 建筑的监测点
curl "http://localhost:3000/api/query/meters?building_id=B001"
```

---

### 1.4 获取设备运行状态

**接口**: `GET /api/query/device-status`

**功能**: 获取设备运行状态统计

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 否 | 建筑编号 |
| meter_id | string | 否 | 监测点编号 |
| status | string | 否 | 状态筛选 (normal/abnormal) |

**响应示例**:
```json
{
  "code": 200,
  "data": [
    {
      "meter_id": "M001",
      "building_id": "B001",
      "type": "电表",
      "status": "normal",
      "data_count": 1000,
      "last_update": "2024-03-07 10:00:00",
      "avg_power": 125.6,
      "anomaly_count": 5
    }
  ]
}
```

**使用示例**:
```bash
# 查看所有设备状态
curl "http://localhost:3000/api/query/device-status"

# 查看异常设备
curl "http://localhost:3000/api/query/device-status?status=abnormal"
```

---

## 📊 2. 统计分析 API (`/api/statistics`)

### 2.1 时段汇总统计

**接口**: `GET /api/statistics/summary`

**功能**: 按时间段汇总统计能耗数据

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| building_id | string | 是 | - | 建筑编号 |
| start_date | string | 是 | - | 开始日期 |
| end_date | string | 是 | - | 结束日期 |
| group_by | string | 否 | day | 分组方式 (day/week/month) |

**响应示例**:
```json
{
  "building_id": "B001",
  "period": "2024-03-01 至 2024-03-07",
  "group_by": "day",
  "details": [
    {
      "period": "2024-03-01",
      "total_elec": 1250.5,
      "avg_elec": 52.1,
      "max_elec": 180.3,
      "min_elec": 20.5,
      "std_elec": 35.2,
      "total_water": 50.2,
      "data_points": 24
    }
  ],
  "summary": {
    "total_elec": 8753.5,
    "avg_elec": 52.1,
    "total_water": 351.4
  }
}
```

**使用示例**:
```bash
# 按日统计
curl "http://localhost:3000/api/statistics/summary?building_id=B001&start_date=2024-03-01&end_date=2024-03-07&group_by=day"

# 按月统计
curl "http://localhost:3000/api/statistics/summary?building_id=B001&start_date=2024-01&end_date=2024-03&group_by=month"
```

---

### 2.2 计算能效比 (COP)

**接口**: `GET /api/statistics/cop`

**功能**: 计算制冷系统能效比

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 是 | 建筑编号 |
| start_date | string | 是 | 开始日期 |
| end_date | string | 是 | 结束日期 |

**响应示例**:
```json
{
  "building_id": "B001",
  "period": "2024-03-01 至 2024-03-07",
  "data": [
    {
      "timestamp": "2024-03-07 10:00:00",
      "electricity": 125.6,
      "supply_temp": 7.0,
      "return_temp": 12.0,
      "cop": 3.5
    }
  ],
  "average_cop": 3.8
}
```

**使用示例**:
```bash
curl "http://localhost:3000/api/statistics/cop?building_id=B001&start_date=2024-03-01&end_date=2024-03-07"
```

---

### 2.3 获取异常列表

**接口**: `GET /api/statistics/anomaly`

**功能**: 获取能耗异常数据列表

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| building_id | string | 否 | - | 建筑编号 |
| start_date | string | 否 | - | 开始日期 |
| end_date | string | 否 | - | 结束日期 |
| limit | integer | 否 | 10 | 返回数量限制 |

**响应示例**:
```json
{
  "building_id": "B001",
  "period": "2024-03-01 至 2024-03-07",
  "anomaly_count": 5,
  "anomalies": [
    {
      "timestamp": "2024-03-05 14:00:00",
      "electricity": 350.2,
      "expected_value": 150.0,
      "deviation": 200.2,
      "z_score": 3.5,
      "type": "用电突增"
    }
  ]
}
```

**使用示例**:
```bash
# 获取 B001 建筑的异常数据
curl "http://localhost:3000/api/statistics/anomaly?building_id=B001&limit=10"

# 获取指定时间段的异常
curl "http://localhost:3000/api/statistics/anomaly?building_id=B001&start_date=2024-03-01&end_date=2024-03-07"
```

---

## 📈 3. 图表数据 API (`/api/charts`)

### 3.1 获取趋势图数据

**接口**: `GET /api/charts/trend`

**功能**: 获取 ECharts 趋势图数据（折线图）

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| building_id | string | 是 | - | 建筑编号 |
| days | integer | 否 | 7 | 天数 (1-30) |

**响应示例**:
```json
{
  "code": 200,
  "data": {
    "categories": [
      "2024-03-01 0:00",
      "2024-03-01 1:00",
      "2024-03-01 2:00"
    ],
    "series": [
      {
        "name": "平均用电量",
        "type": "line",
        "data": [120.5, 115.3, 108.7],
        "smooth": true
      },
      {
        "name": "最大用电量",
        "type": "line",
        "data": [150.2, 145.8, 138.5],
        "smooth": true,
        "lineStyle": {"type": "dashed"}
      }
    ]
  }
}
```

**使用示例**:
```bash
# 获取最近 7 天趋势
curl "http://localhost:3000/api/charts/trend?building_id=B001&days=7"

# 获取最近 30 天趋势
curl "http://localhost:3000/api/charts/trend?building_id=B001&days=30"
```

---

### 3.2 获取对比数据

**接口**: `GET /api/charts/comparison`

**功能**: 获取多建筑对比数据（柱状图）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_ids | string | 是 | 逗号分隔的建筑编号，如 "B001,B002,B003" |
| start_date | string | 是 | 开始日期 |
| end_date | string | 是 | 结束日期 |

**响应示例**:
```json
{
  "code": 200,
  "data": {
    "categories": ["总能耗", "平均能耗", "峰值能耗"],
    "series": [
      {
        "name": "行政楼",
        "data": [350.5, 14.6, 180.3]
      },
      {
        "name": "实验楼",
        "data": [280.3, 11.7, 150.8]
      }
    ]
  }
}
```

**使用示例**:
```bash
# 对比三个建筑
curl "http://localhost:3000/api/charts/comparison?building_ids=B001,B002,B003&start_date=2024-03-01&end_date=2024-03-07"
```

---

### 3.3 获取分布图数据

**接口**: `GET /api/charts/distribution`

**功能**: 获取能耗分布数据（饼图/环形图）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 否 | 建筑编号（不传则查询所有建筑） |
| date | string | 否 | 日期 (YYYY-MM-DD)，默认今天 |

**响应示例**:
```json
{
  "code": 200,
  "data": {
    "data": {
      "series": [
        {"name": "行政楼", "value": 350.5},
        {"name": "实验楼", "value": 280.3},
        {"name": "教学楼 A", "value": 220.8}
      ]
    }
  }
}
```

**使用示例**:
```bash
# 查询所有建筑今日能耗分布
curl "http://localhost:3000/api/charts/distribution"

# 查询指定建筑
curl "http://localhost:3000/api/charts/distribution?building_id=B001&date=2024-03-07"
```

---

## 💬 4. 智能问答 API (`/api/chat`)

### 4.1 智能问答

**接口**: `POST /api/chat/ask`

**功能**: 基于 RAG 的智能问答系统

**请求体**:
```json
{
  "query": "B001 建筑昨天用电量是多少？",
  "building_id": "B001",
  "session_id": "session_001"
}
```

**响应示例**:
```json
{
  "answer": "建筑 B001 昨天的用电量为 1250.5 kWh",
  "type": "data",
  "data": {
    "value": 1250.5
  }
}
```

**回答类型说明**:
- `data`: 数据查询结果
- `knowledge`: 运维知识
- `help`: 帮助信息
- `error`: 错误信息

**使用示例**:
```bash
# 查询能耗数据
curl -X POST "http://localhost:3000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "B001 昨天用电量是多少？", "building_id": "B001"}'

# 查询运维知识
curl -X POST "http://localhost:3000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "冷水机组故障怎么处理？"}'
```

---

## 🔧 5. MCP 协议 API (`/mcp`)

### 5.1 MCP 聊天完成

**接口**: `POST /mcp/v1/chat/completions`

**功能**: MCP 协议标准接口，支持工具调用

**请求体**:
```json
{
  "model": "energy-ai",
  "messages": [
    {
      "role": "user",
      "content": "查询 B001 建筑能耗"
    }
  ],
  "tools": [
    {
      "tool": "query_energy_data",
      "arguments": {
        "building_id": "B001",
        "start_time": "2024-03-01",
        "end_time": "2024-03-07",
        "metrics": ["electricity"]
      },
      "id": "call_001"
    }
  ]
}
```

**响应示例**:
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "role": "tool",
            "content": "{\"building_id\":\"B001\",\"total\":1250.5}",
            "tool_call_id": "call_001"
          }
        ]
      }
    }
  ]
}
```

**使用示例**:
```bash
curl -X POST "http://localhost:3000/mcp/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "energy-ai",
    "messages": [{"role": "user", "content": "查询 B001 建筑能耗"}],
    "tools": [{
      "tool": "query_energy_data",
      "arguments": {
        "building_id": "B001",
        "start_time": "2024-03-01",
        "end_time": "2024-03-07"
      },
      "id": "call_001"
    }]
  }'
```

---

### 5.2 列出可用工具

**接口**: `GET /mcp/v1/tools`

**功能**: 列出所有可用的 MCP 工具

**响应示例**:
```json
{
  "tools": [
    {
      "name": "query_energy_data",
      "description": "查询建筑能耗数据",
      "parameters": {
        "building_id": {"type": "string", "description": "建筑编号"},
        "start_time": {"type": "string", "description": "开始时间"},
        "end_time": {"type": "string", "description": "结束时间"},
        "metrics": {"type": "array", "description": "查询指标"}
      }
    },
    {
      "name": "analyze_anomaly",
      "description": "分析能耗异常",
      "parameters": {
        "building_id": {"type": "string", "description": "建筑编号"},
        "start_date": {"type": "string", "description": "开始日期"},
        "end_date": {"type": "string", "description": "结束日期"},
        "threshold": {"type": "number", "description": "异常阈值"}
      }
    }
  ]
}
```

**使用示例**:
```bash
curl "http://localhost:3000/mcp/v1/tools"
```

---

## 📤 6. 报表导出 API (`/api/export`)

### 6.1 导出 CSV 报表

**接口**: `GET /api/export/csv`

**功能**: 导出 CSV 格式的能耗报表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 是 | 建筑编号 |
| start_date | string | 是 | 开始日期 |
| end_date | string | 是 | 结束日期 |

**响应**: CSV 文件下载

**使用示例**:
```bash
# 下载 CSV 文件
curl "http://localhost:3000/api/export/csv?building_id=B001&start_date=2024-03-01&end_date=2024-03-07" \
  --output energy_B001_2024-03-01.csv
```

---

### 6.2 导出 Excel 报表

**接口**: `GET /api/export/excel`

**功能**: 导出 Excel 格式的能耗报表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 是 | 建筑编号 |
| start_date | string | 是 | 开始日期 |
| end_date | string | 是 | 结束日期 |

**响应**: Excel 文件下载

**使用示例**:
```bash
# 下载 Excel 文件
curl "http://localhost:3000/api/export/excel?building_id=B001&start_date=2024-03-01&end_date=2024-03-07" \
  --output energy_B001_2024-03-01.xlsx
```

---

### 6.3 导出 PDF 报表

**接口**: `GET /api/export/pdf`

**功能**: 导出 PDF 格式的能耗报表（支持中文）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| building_id | string | 是 | 建筑编号 |
| start_date | string | 是 | 开始日期 |
| end_date | string | 是 | 结束日期 |

**响应**: PDF 文件下载

**使用示例**:
```bash
# 下载 PDF 文件
curl "http://localhost:3000/api/export/pdf?building_id=B001&start_date=2024-03-01&end_date=2024-03-07" \
  --output energy_report_B001.pdf
```

---

## 🔍 7. 健康检查

### 7.1 根路径

**接口**: `GET /`

**功能**: 获取应用基本信息

**响应示例**:
```json
{
  "app_name": "建筑能源管理系统",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

**使用示例**:
```bash
curl "http://localhost:3000/"
```

---

### 7.2 健康检查

**接口**: `GET /api/health`

**功能**: 检查应用和数据库健康状态

**响应示例**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-03-07T10:00:00"
}
```

**使用示例**:
```bash
curl "http://localhost:3000/api/health"
```

---

## 📝 快速开始示例

### 1. 查询建筑列表
```bash
curl "http://localhost:3000/api/query/buildings"
```

### 2. 查询某建筑今日能耗
```bash
curl "http://localhost:3000/api/statistics/summary?building_id=B001&start_date=2024-03-07&end_date=2024-03-07&group_by=day"
```

### 3. 获取近 7 天趋势图
```bash
curl "http://localhost:3000/api/charts/trend?building_id=B001&days=7"
```

### 4. 智能问答
```bash
curl -X POST "http://localhost:3000/api/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "B001 建筑今天用电量是多少？"}'
```

### 5. 导出 Excel 报表
```bash
curl "http://localhost:3000/api/export/excel?building_id=B001&start_date=2024-03-01&end_date=2024-03-07" \
  --output report.xlsx
```

---

## ⚠️ 注意事项

1. **所有日期格式**: `YYYY-MM-DD` (如：`2024-03-07`)
2. **时间戳格式**: `YYYY-MM-DD HH:mm:ss` (如：`2024-03-07 10:00:00`)
3. **建筑编号**: 通常为 `B001`, `B002` 等
4. **响应码**: 
   - `200`: 成功
   - `400`: 请求参数错误
   - `404`: 资源不存在
   - `500`: 服务器内部错误

---

## 🛠️ 技术支持

- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc
- **项目文档**: [README.md](README.md)
