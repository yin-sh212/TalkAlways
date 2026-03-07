# 数据查询与分析页面实现说明

## 功能概述
已实现完整的"数据查询与分析"（Analysis）页面，包含以下功能模块：

### 1. 顶部查询条件栏
- **建筑选择**：下拉多选框，支持搜索建筑名称（5 个 Mock 建筑选项）
- **参数选择**：下拉单选（电力能耗、空调能耗、环境温度、COP 值）
- **时间范围**：双日历选择器 + 快捷按钮（今日、本周、本月）
- **自然语言输入框**：支持输入自然语言查询，按回车自动解析
- **操作按钮**：查询（主按钮）、重置

### 2. 结果展示区
#### Tab 1 - 数据表格
- 展示查询返回的原始数据
- 支持列排序（时间、建筑名称、数值）
- 支持每页 10/20/50 条切换
- 异常数据红色高亮显示

#### Tab 2 - 分析视图
**左侧图表区：**
- 图表 1：能耗趋势折线图（默认）
  - 支持异常点标记（红色显示）
  - 鼠标悬停显示详细信息
  - 右上角放大图标可弹窗查看大图
- 图表 2：能耗分布柱状图（默认）
  - 展示各建筑能耗对比
  - 支持放大查看

**右侧指标卡：**
- 查询时段总能耗（MWh）
- 平均能耗（MWh）
- 异常点数（红色高亮）

### 3. 底部操作栏
- 固定在页面右下角
- 导出报表按钮
- 显示"生成中..."Toast 提示

## 技术实现

### 依赖库
- **Naive UI**：UI 组件库（表单、表格、卡片、标签页等）
- **ECharts**：图表库（折线图、柱状图）
- **@vicons/ionicons5**：图标库
- **Vue 3 + TypeScript**：响应式框架和类型系统

### 核心功能

#### 1. 自然语言查询（NL2Query）
```typescript
// 当前实现：Mock 解析结果
const mockParsedResult = {
  buildings: ['building-001'],
  parameter: 'hvac',
  timeRange: [Date.now() - 7 * 24 * 3600 * 1000, Date.now()]
}

// 待对接：调用后端解析接口
// const parsedResult = await parseNaturalQuery(queryForm.naturalQuery)
```

#### 2. 数据查询
```typescript
// 当前实现：生成 Mock 数据
const mockData = generateMockData()

// 待对接：调用后端查询接口
// const result = await queryData(queryForm)
```

#### 3. 图表异常高亮
- 折线图中异常点使用红色标记
- 鼠标悬停显示"异常点（算法标记）"
- 通过 `markPoint` 标记最大值

#### 4. 图表放大功能
- 点击图表右上角放大图标
- 弹窗展示大图（90% 屏幕宽度）
- 自适应窗口大小

#### 5. 导出报表
- 显示"生成中..."提示
- 模拟 2 秒延迟
- 下载完成后自动关闭提示

### 文件结构
```
client/src/
├── views/
│   └── Analysis.vue          # 数据查询与分析页面
├── api/
│   └── analysis.ts           # Analysis API 接口
└── types/
    └── analysis.ts           # Analysis 相关类型定义
```

### 路由配置
已在 `router/index.ts` 中配置：
```typescript
{
  path: '/analysis',
  name: 'Analysis',
  component: () => import('@/views/Analysis.vue'),
  meta: { requiresAuth: true }
}
```

## Mock 数据说明

### 建筑选项
- 行政楼 (building-001)
- 教学楼 A (building-002)
- 教学楼 B (building-003)
- 图书馆 (building-004)
- 实验楼 (building-005)

### 参数选项
- electricity (电力能耗)
- hvac (空调能耗)
- temperature (环境温度)
- cop (COP 值)

### 查询结果
- 自动生成 7 天 × 5 建筑 = 35 条数据
- 10% 概率标记为异常
- 随机生成能耗值（20-70 MWh）

## 后端接口对接

### 1. NL2Query 解析接口
**接口路径**：`POST /analysis/nl2query`

**请求参数**：
```typescript
{
  query: string // 自然语言查询文本
  context?: any // 上下文信息
}
```

**响应格式**：
```typescript
{
  code: number,
  message: string,
  data: {
    buildings: string[],
    parameter: string,
    timeRange: [number, number],
    confidence: number
  }
}
```

### 2. 数据查询接口
**接口路径**：`POST /analysis/query`

**请求参数**：
```typescript
{
  buildings: string[],
  parameter: string,
  startTime: number,
  endTime: number,
  pageSize?: number,
  pageNum?: number
}
```

**响应格式**：
```typescript
{
  code: number,
  message: string,
  data: {
    list: QueryDataItem[],
    total: number,
    metrics: {
      totalEnergy: number,
      avgEnergy: number,
      anomalyCount: number
    }
  }
}
```

### 3. 导出报表接口
**接口路径**：`POST /analysis/export`

**请求参数**：
```typescript
{
  buildings: string[],
  parameter: string,
  startTime: number,
  endTime: number,
  format?: 'excel' | 'csv' | 'pdf'
}
```

**响应格式**：Blob 二进制流

## 待实现功能

以下功能已预留接口位置，需要后端支持：

1. **NL2Query 解析**：在 `handleNaturalQuery` 函数中调用
2. **数据查询**：在 `handleQuery` 函数中调用
3. **报表导出**：在 `handleExport` 函数中调用

## 使用示例

### 1. 访问页面
访问 `http://localhost:8081/analysis` 即可看到完整页面

### 2. 自然语言查询示例
输入："A 栋上周每天的空调电耗"
- 自动解析出：建筑=A 栋，参数=空调能耗，时间=上周
- 自动填充到查询条件栏
- 自动执行查询

### 3. 快捷时间选择
- **今日**：当天 00:00 - 23:59
- **本周**：本周日 - 本周六
- **本月**：本月 1 日 - 月末

### 4. 异常高亮
- 表格中异常数据红色显示
- 折线图中异常点红色标记
- 指标卡显示异常点总数

## 注意事项

1. **数据初始化规范**：
   - 所有响应式数据已在 setup 中显式定义
   - Mock 数据在查询时生成
   - 图表初始化与数据更新分离

2. **数据安全访问**：
   - 使用了可选链操作符
   - 添加了条件渲染
   - 符合 Vue 组件开发规范

3. **图表自适应**：
   - 监听窗口 resize 事件
   - 自动调整图表尺寸
   - 弹窗图表延迟初始化

4. **类型安全**：
   - 所有 API 响应有明确类型定义
   - 避免隐式 any 类型
   - 函数参数显式声明类型
