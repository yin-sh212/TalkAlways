# 后端接口配置说明

## 当前配置

### Vite 代理配置
位置：`client/vite.config.ts`
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:3000',  // 后端服务地址
      changeOrigin: true
    }
  }
}
```

### 前端 API 调用
所有接口请求都会通过 Vite 代理转发到后端：
- 前端请求：`http://localhost:8080/api/xxx`
- 代理转发：`http://localhost:3000/api/xxx`

## 后端服务要求

### 方案 1：后端运行在 3000 端口（推荐）

**后端需要做的修改：**
1. 将后端服务端口改为 **3000**
2. 确保后端接口路径包含 `/api` 前缀

**接口示例：**
```
GET  http://localhost:3000/api/statistics/summary?period=today&type=total_energy
GET  http://localhost:3000/api/charts/distribution?period=today&type=building_ratio
GET  http://localhost:3000/api/charts/trend?period=7days&type=total_energy
GET  http://localhost:3000/api/statistics/anomaly?limit=5&order=desc
POST http://localhost:3000/api/chat/ask
POST http://localhost:3000/api/query/raw
GET  http://localhost:3000/api/statistics/summary
GET  http://localhost:3000/api/statistics/anomaly
POST http://localhost:3000/api/export/excel
```

**优点：**
- 无需修改前端配置
- 符合开发环境约定
- 代理自动处理跨域

### 方案 2：修改 Vite 代理配置

如果后端必须运行在 8080 以外的其他端口（比如 5000），可以修改 Vite 配置：

**修改 `client/vite.config.ts`：**
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',  // 改为实际后端端口
      changeOrigin: true
    }
  }
}
```

**然后重启前端服务：**
```bash
cd client
npm run dev
```

### 方案 3：后端运行在 8080 端口（不推荐）

如果后端也运行在 8080 端口，需要：
1. 前端更换端口（比如 3001）
2. 或者后端使用其他路径前缀（避免冲突）

**不推荐此方案**，因为会导致端口冲突。

## 接口格式要求

### 统一响应格式
后端所有接口应返回以下格式：
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }  // 实际业务数据
}
```

### 具体接口定义

#### 1. KPI 数据接口
```
GET /api/statistics/summary
Query Params:
  - period: string (today)
  - type: string (total_energy)

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "totalEnergy": 1256.8,
    "energyChange": -3.5,
    "deviceOnlineRate": 98,
    "abnormalDeviceCount": 2,
    "co2Reduction": 856.4
  }
}
```

#### 2. 建筑能耗占比
```
GET /api/charts/distribution
Query Params:
  - period: string (today)
  - type: string (building_ratio)

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "buildingEnergy": [
      { "name": "行政楼", "value": 350.5, "percentage": 28 },
      { "name": "教学楼 A", "value": 280.3, "percentage": 22 }
    ],
    "trendData": [
      { "date": "2024-01-01", "energy": 1156.5 }
    ]
  }
}
```

#### 3. 能耗趋势
```
GET /api/charts/trend
Query Params:
  - period: string (7days)
  - type: string (total_energy)

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "trendData": [
      { "date": "2024-01-01", "energy": 1156.5 },
      { "date": "2024-01-02", "energy": 1189.3 }
    ]
  }
}
```

#### 4. 异常列表
```
GET /api/statistics/anomaly
Query Params:
  - limit: number (5)
  - order: string (desc)

Response:
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "1",
      "time": "2024-01-07 14:35:20",
      "buildingName": "行政楼",
      "type": "能耗突增",
      "status": "pending",
      "buildingId": "building-001",
      "timeRange": {
        "start": "2024-01-07T00:00:00",
        "end": "2024-01-07T23:59:59"
      }
    }
  ]
}
```

#### 5. 自然语言查询
```
POST /api/chat/ask
Body:
{
  "query": "A 栋上周每天的空调电耗"
}

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "buildings": ["building-001"],
    "parameter": "hvac",
    "timeRange": [1704672000000, 1705276800000],
    "confidence": 0.95
  }
}
```

#### 6. 数据查询
```
POST /api/query/raw
Body:
{
  "buildings": ["building-001"],
  "parameter": "electricity",
  "startTime": 1704672000000,
  "endTime": 1705276800000,
  "pageSize": 10,
  "pageNum": 1
}

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "time": "2024-01-01 00:00:00",
        "buildingId": "building-001",
        "buildingName": "行政楼",
        "parameterName": "电力能耗",
        "value": 150.5,
        "unit": "MWh",
        "isAnomaly": false
      }
    ],
    "total": 100
  }
}
```

#### 7. 统计摘要
```
GET /api/statistics/summary
Query Params:
  - buildings: string[]
  - parameter: string
  - startTime: number
  - endTime: number

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "metrics": {
      "totalEnergy": 1256.8,
      "avgEnergy": 179.54
    }
  }
}
```

#### 8. 异常统计
```
GET /api/statistics/anomaly
Query Params:
  - buildings: string[]
  - parameter: string
  - startTime: number
  - endTime: number

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "count": 5
  }
}
```

#### 9. 导出报表
```
POST /api/export/excel
Body:
{
  "buildings": ["building-001"],
  "parameter": "electricity",
  "startTime": 1704672000000,
  "endTime": 1705276800000,
  "format": "excel"
}

Response: 
二进制文件流 (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
```

## 开发流程

### 1. 启动后端服务
确保后端运行在 **3000 端口**：
```bash
# 后端项目
npm run dev  # 或 python app.py 等
```

### 2. 启动前端服务
```bash
cd client
npm run dev
```

前端会自动将 `/api` 请求代理到 `http://localhost:3000`

### 3. 访问应用
打开浏览器访问：`http://localhost:8080`

### 4. 验证接口
在浏览器开发者工具的 Network 面板查看：
- 请求地址应该是 `http://localhost:8080/api/xxx`
- 实际会被代理到 `http://localhost:3000/api/xxx`

## 常见问题

### Q1: 500 Internal Server Error
**原因**：后端服务未启动或接口路径错误  
**解决**：
1. 确认后端服务运行在 3000 端口
2. 检查接口路径是否包含 `/api` 前缀
3. 查看后端日志定位具体错误

### Q2: 404 Not Found
**原因**：接口路径不正确  
**解决**：
1. 确认后端接口路径包含 `/api` 前缀
2. 检查 Vite 代理配置是否正确

### Q3: 跨域错误
**原因**：代理未生效  
**解决**：
1. 确保通过 Vite 开发服务器访问（http://localhost:8080）
2. 不要直接访问后端地址（http://localhost:3000）
3. 重启 Vite 开发服务器

### Q4: 端口冲突
**原因**：8080 或 3000 端口被占用  
**解决**：
```bash
# Windows - 查找占用端口的进程
netstat -ano | findstr :8080
taskkill /F /PID <进程 ID>

# 或修改 Vite 端口配置
server: {
  port: 3001  # 改为其他端口
}
```

## 下一步

1. **后端修改端口到 3000**
2. **确保所有接口包含 `/api` 前缀**
3. **重启前端开发服务器**
4. **测试接口调用**

完成后前端将自动调用后端真实接口！🎉
