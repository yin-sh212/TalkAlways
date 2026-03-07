// 仪表盘相关类型定义

// KPI 数据
export interface KPIData {
  totalEnergy: number
  energyChange: number
  dayChange: number // 日环比
  weekChange: number // 周同比
  deviceOnlineRate: number
  abnormalDeviceCount: number
  co2Reduction: number
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
