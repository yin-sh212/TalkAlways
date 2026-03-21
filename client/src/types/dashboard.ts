// 仪表盘相关类型定义

// KPI 数据
export interface KPIData {
  totalEnergy: number
  energyChange: number
  dayChange: number // 日环比
  weekChange: number // 周同比
  deviceOnlineRate: number
  abnormalDeviceCount: number
  cop: number // COP(能效比)
  // co2Reduction: number // 已注释，不再使用
}

// 图表数据
export interface ChartData {
  buildingEnergy?: Array<{
    name: string
    value: number
    percentage?: number
  }>
  trendData?: Array<{
    date: string
    energy: number
  }>
  categories?: string[]
  series?: Array<{
    name: string
    type: string
    data: number[]
    smooth?: boolean
    areaStyle?: any
    lineStyle?: any
  }>
}

// 异常项
export interface AnomalyItem {
  id: string | number
  time: string
  buildingName: string
  type: string
  status: 'pending' | 'processing' | 'resolved'
  buildingId: string
  timeRange: {
    start: string
    end: string
  }
}

// 通用响应包装（后端实际格式）
export interface DashboardResponse<T> {
  code: number
  message?: string
  data: T
}

// Summary 接口返回的数据结构
export interface SummaryResponse {
  building_id: string
  period: string
  time_unit: string
  details: any[]
  summary: {
    total_elec: number | null
    avg_elec: number | null
    total_water: number | null
  }
}

// Distribution 接口返回的数据结构
export interface DistributionResponse {
  categories: string[]
  series: Array<{
    name: string
    type: string
    data: number[]
    areaStyle?: any
  }>
}

// Trend 接口返回的数据结构
export interface TrendResponse {
  categories: string[]
  series: Array<{
    name: string
    type: string
    data: number[]
    smooth?: boolean
    lineStyle?: any
  }>
}

// Anomaly 接口返回的数据结构
export interface AnomalyResponse {
  building_id: string
  period: string
  total_points: number
  anomaly_count: number
  anomalies: any[]
}
