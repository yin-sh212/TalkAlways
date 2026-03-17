// 分析查询相关类型定义

// 自然语言查询参数
export interface NL2QueryParams {
  query: string // 自然语言查询文本
  context?: {
    building_id?: string
    session_id?: string
  }
}

// 自然语言查询响应（后端实际返回）
export interface NL2QueryResult {
  answer: string
  type: string
  sources?: any[]
  data?: {
    value?: number
  }
}

export interface NL2QueryResponse {
  answer: string
  type: string
  sources?: any[]
  data?: any
}

// 数据查询参数
export interface QueryParams {
  buildings: string[] // 建筑 ID 列表
  parameter: string // 参数类型
  startTime: number // 开始时间戳
  endTime: number // 结束时间戳
  pageSize?: number // 每页大小
  pageNum?: number // 页码
}

// 查询结果数据项（后端实际返回）
export interface QueryDataItem {
  id?: number
  timestamp: string
  building_id: string
  meter_id?: string
  electricity: number
  water?: number
  ambient_temp?: number
  humidity?: number
  is_anomaly?: number | boolean
}

// 查询响应（后端实际格式）
export interface QueryResponse {
  code: number
  data: QueryDataItem[]
  pagination?: {
    total: number
    limit: number
    offset: number
    has_more: boolean
  }
}

// 统计摘要参数
export interface StatisticsParams {
  buildings: string[]
  parameter: string
  startTime: number
  endTime: number
}

// 统计摘要响应（后端实际返回）
export interface StatisticsResponse {
  building_id: string
  period: string
  group_by: string
  details: any[]
  summary: {
    total_elec: number
    avg_elec: number
    total_water?: number
  }
}

// 异常统计参数
export interface AnomalyCountParams {
  buildings: string[]
  parameter: string
  startTime: number
  endTime: number
}

// 异常统计响应（后端实际返回）
export interface AnomalyCountResponse {
  building_id: string
  period: string
  threshold: string
  total_points: number
  anomaly_count: number
  anomalies: any[]
}

// 导出参数
export interface ExportParams {
  buildings: string[]
  parameter: string
  startTime: number
  endTime: number
  format?: 'excel' | 'csv' | 'pdf'
}

// 建筑能耗详情数据结构（新）
export interface BuildingEnergyDetail {
  period: string // 日期期间，如 "2016-07-14"
  data_points: number // 数据点数
  total_elec: number // 总电量
  avg_elec: number // 平均电量
  max_elec: number // 最大电量
  min_elec: number // 最小电量
  std_elec: number // 标准差
  total_cooling: number // 总冷量
  avg_cooling: number // 平均冷量
  max_cooling: number // 最大冷量
  min_cooling: number // 最小冷量
  total_heating: number // 总热量
  avg_heating: number // 平均热量
  max_heating: number // 最大热量
  min_heating: number // 最小热量
  avg_temp: number // 平均温度
  max_temp: number // 最高温度
  min_temp: number // 最低温度
  avg_pressure: number // 平均压力
}

// 汇总统计
export interface EnergySummary {
  total_points?: number // 总数据点数
  total_elec: number | null // 总电量
  avg_elec: number | null // 平均电量
  total_cooling?: number // 总冷量
  avg_cooling?: number // 平均冷量
  total_heating?: number // 总热量
  avg_heating?: number // 平均热量
  avg_temp?: number // 平均温度
  avg_pressure?: number // 平均压力
  total_water?: number | null // 总水量（兼容旧版）
}

// 建筑能耗详情响应
export interface BuildingEnergyDetailResponse {
  building_id: string
  period: string // 时间段描述，如 "2016-07-14 至 2016-07-15"
  time_unit: string // 时间单位，如 "day"
  include_fields: string // 包含字段，如 "all"
  details: BuildingEnergyDetail[] // 详细数据数组
  summary: EnergySummary // 汇总统计
}
