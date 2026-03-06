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
