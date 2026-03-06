// 仪表盘相关类型定义

// KPI 数据
export interface KPIData {
  totalEnergy: number // 今日总能耗 (MWh)
  energyChange: number // 同比变化百分比
  deviceOnlineRate: number // 在线设备率 (%)
  abnormalDeviceCount: number // 异常设备数量
  co2Reduction: number // CO₂减排量 (kg)
}

// 图表数据
export interface BuildingEnergyItem {
  name: string // 建筑名称
  value: number // 能耗值
  percentage: number // 占比
}

export interface TrendDataItem {
  date: string // 日期
  energy: number // 能耗值
}

export interface ChartData {
  buildingEnergy: BuildingEnergyItem[] // 各建筑能耗
  trendData: TrendDataItem[] // 趋势数据
}

// 异常项
export interface AnomalyItem {
  id: string
  time: string // 异常时间
  buildingName: string // 建筑名称
  type: string // 异常类型
  status: 'pending' | 'processing' | 'resolved' // 状态
  buildingId: string // 建筑 ID
  timeRange: {
    start: string
    end: string
  }
}

// API 响应数据类型
export interface DashboardResponse<T = any> {
  code: number
  message: string
  data: T
}
