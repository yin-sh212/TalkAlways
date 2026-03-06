# 核心页面后端接口对接说明

## 概述
已完成首页（仪表盘）和数据查询与分析页的后端接口对接，所有接口均已配置为调用真实后端 API。

---

## 一、首页（仪表盘）- Overview.vue

### 1. 接口调用逻辑（并行调用）

#### 1.1 顶部 KPI 卡片
**接口**: `GET /statistics/summary`  
**参数**: 
- `period=today`
- `type=total_energy`

**用途**: 填充今日总能耗、同比增减、异常设备数、CO₂减排量

**代码位置**: `dashboardApi.getKPIData()`

#### 1.2 各建筑能耗占比（环形图）
**接口**: `GET /charts/distribution`  
**参数**: 
- `period=today`
- `type=building_ratio`

**用途**: 渲染环形图，支持鼠标悬停显示建筑名称 + 能耗/占比

**代码位置**: `dashboardApi.getChartData()`

#### 1.3 近 7 日总能耗趋势（折线图）
**接口**: `GET /charts/trend`  
**参数**: 
- `period=7days`
- `type=total_energy`

**用途**: 渲染 7 日趋势折线图，支持鼠标悬停显示日期 + 具体能耗值

**代码位置**: `dashboardApi.getTrendData()`

#### 1.4 底部异常列表（最新 5 条）
**接口**: `GET /statistics/anomaly`  
**参数**: 
- `limit=5`
- `order=desc`（按时间倒序）

**用途**: 展示异常时间、建筑名称、异常类型、状态

**代码位置**: `dashboardApi.getAnomalyList(5)`

### 2. 核心函数

```typescript
// 并行调用所有接口
const loadData = async () => {
  const [kpiRes, distributionRes, trendRes, anomalyRes] = await Promise.all([
    dashboardApi.getKPIData(),
    dashboardApi.getChartData(),
    dashboardApi.getTrendData(),
    dashboardApi.getAnomalyList(5)
  ])
  
  kpiData.value = kpiRes.data.data
  chartData.value = {
    buildingEnergy: distributionRes.data.data.buildingEnergy,
    trendData: trendRes.data.data.trendData
  }
  anomalyList.value = anomalyRes.data.data
  
  initCharts()
}
```

### 3. 交互衔接

#### 异常列表点击跳转
**触发**: 点击任意异常项或"查看详情"按钮  
**跳转参数**: 
- `building`: 建筑 ID
- `start`: 异常开始时间
- `end`: 异常结束时间

**跳转方法**: `dashboardApi.navigateToAnalysis(buildingId, timeRange)`

---

## 二、数据查询与分析页 - Analysis.vue

### 1. 自然语言查询（NL2Query）

#### 接口调用
**接口**: `POST /chat/ask`  
**参数**: 
```typescript
{
  query: "A 栋上周每天的空调电耗"
}
```

**响应结构**:
```typescript
{
  code: number,
  message: string,
  data: {
    buildings: string[],      // ['building-001']
    parameter: string,         // 'hvac'
    timeRange: [number, number], // [startTime, endTime]
    confidence: number
  }
}
```

**代码位置**: `analysisApi.parseNaturalQuery()`

#### 自动回填
解析成功后自动填充到：
- 建筑选择下拉框
- 参数选择下拉框
- 时间范围选择器

### 2. 核心查询逻辑（统一触发）

#### 2.1 数据表格（Tab 1）
**接口**: `POST /query/raw`  
**参数**: 
```typescript
{
  buildings: string[],
  parameter: string,
  startTime: number,
  endTime: number,
  pageSize: number,
  pageNum: number
}
```

**用途**: 展示原始能耗数据，支持排序、分页切换

#### 2.2 分析视图 - 左侧图表（Tab 2）
**接口 1**: `POST /query/raw`（趋势数据）  
**接口 2**: `POST /query/raw`（分布数据）

**用途**: 
- 能耗趋势折线图（标记异常点为红色）
- 能耗分布柱状图

**异常点标记**: 
- 红色高亮显示
- 鼠标悬停显示"异常点（算法标记）"

#### 2.3 分析视图 - 右侧指标卡（Tab 2）

##### 总能耗 + 平均能耗
**接口**: `GET /statistics/summary`  
**参数**: 
```typescript
{
  buildings: string[],
  parameter: string,
  startTime: number,
  endTime: number
}
```

**响应**:
```typescript
{
  data: {
    metrics: {
      totalEnergy: number,
      avgEnergy: number
    }
  }
}
```

##### 异常点数
**接口**: `GET /statistics/anomaly`  
**参数**: 同上

**响应**:
```typescript
{
  data: {
    count: number
  }
}
```

### 3. 导出报表

#### 接口调用
**接口**: `POST /export/{format}`  
**参数**: 
```typescript
{
  buildings: string[],
  parameter: string,
  startTime: number,
  endTime: number,
  format: 'excel' | 'csv' | 'pdf'
}
```

**交互**: 
- 显示"生成中..."Toast
- 下载完成后自动关闭
- 文件名格式：`能耗报表_时间戳.xlsx`

**代码位置**: `analysisApi.exportReport()`

### 4. 路由参数处理

#### 从 Overview 跳转自动填充
**触发时机**: onMounted()  
**解析参数**: 
- `building`: 建筑 ID
- `start`: 开始时间
- `end`: 结束时间

**自动执行**: 填充查询条件后自动调用 `handleQuery()`

---

## 三、API 接口文件

### 1. dashboard.ts（仪表盘接口）

```typescript
// KPI 数据
export const getKPIData = () => {
  return http.get('/statistics/summary', {
    params: { period: 'today', type: 'total_energy' }
  })
}

// 分布图数据
export const getChartData = () => {
  return http.get('/charts/distribution', {
    params: { period: 'today', type: 'building_ratio' }
  })
}

// 趋势图数据
export const getTrendData = () => {
  return http.get('/charts/trend', {
    params: { period: '7days', type: 'total_energy' }
  })
}

// 异常列表
export const getAnomalyList = (limit = 5) => {
  return http.get('/statistics/anomaly', {
    params: { limit, order: 'desc' }
  })
}
```

### 2. analysis.ts（分析查询接口）

```typescript
// 自然语言查询
export const parseNaturalQuery = (params: NL2QueryParams) => {
  return http.post('/chat/ask', params)
}

// 原始数据查询
export const queryData = (params: QueryParams) => {
  return http.post('/query/raw', params)
}

// 统计摘要
export const getStatisticsSummary = (params: StatisticsParams) => {
  return http.get('/statistics/summary', { params })
}

// 异常统计
export const getAnomalyCount = (params: AnomalyCountParams) => {
  return http.get('/statistics/anomaly', { params })
}

// 导出报表
export const exportReport = (params: ExportParams) => {
  return http.post(`/export/${params.format}`, params, {
    responseType: 'blob'
  })
}
```

---

## 四、类型定义文件

### dashboard.ts
- `KPIData`: KPI 数据结构
- `ChartData`: 图表数据结构
- `AnomalyItem`: 异常项结构
- `DashboardResponse`: 通用响应包装

### analysis.ts
- `NL2QueryParams` / `NL2QueryResponse`: 自然语言查询
- `QueryParams` / `QueryResponse`: 数据查询
- `StatisticsParams` / `StatisticsResponse`: 统计摘要
- `AnomalyCountParams` / `AnomalyCountResponse`: 异常统计
- `ExportParams`: 导出参数
- `QueryDataItem`: 查询结果数据项

---

## 五、核心功能实现

### 1. 并行接口调用
```typescript
Promise.all([
  api1(),
  api2(),
  api3(),
  api4()
])
```

### 2. 异常点标记
- 折线图中根据 `isAnomaly` 字段标记红色
- Tooltip 显示"异常点（算法标记）"
- 使用 `itemStyle.color` 动态设置颜色

### 3. 图表自适应
- 监听 window.resize 事件
- 调用 `chart.resize()` 重新渲染

### 4. 数据流
```
用户操作 → 调用接口 → 解析响应 → 更新数据 → 渲染图表
```

---

## 六、后续工作

### 1. 后端接口联调
- 确保所有接口按约定格式返回数据
- 测试异常处理机制
- 验证大数据量性能

### 2. 错误处理优化
- 添加接口超时处理
- 完善错误提示信息
- 添加重试机制

### 3. 性能优化
- 实现接口请求缓存
- 添加数据分页加载
- 优化图表渲染性能

---

## 七、注意事项

### 1. 数据访问路径
所有接口响应都被包装在 `data.data` 中：
```typescript
// 第一层 data 是 Axios 响应
// 第二层 data 是业务数据
kpiData.value = kpiRes.data.data
```

### 2. 类型安全
- 所有响应数据都有明确的类型定义
- 避免使用 `any` 类型
- 使用 TypeScript 严格模式

### 3. 错误处理
- 使用 try-catch 捕获异常
- 显示友好的错误提示
- 记录错误日志便于调试

---

## 八、测试建议

### 1. 功能测试
- ✅ KPI 数据加载
- ✅ 图表渲染
- ✅ 异常列表展示
- ✅ 自然语言查询
- ✅ 数据表格查询
- ✅ 报表导出

### 2. 交互测试
- ✅ 页面刷新
- ✅ 条件筛选
- ✅ 图表放大
- ✅ 异常跳转
- ✅ 重置查询

### 3. 兼容性测试
- Chrome
- Firefox
- Edge
- Safari

---

所有接口已对接完成，可以进行后端联调测试！🎉
