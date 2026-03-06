// 分析查询相关类型定义

// 自然语言查询参数
export interface NL2QueryParams {
  query: string // 自然语言查询文本
  context?: any // 上下文信息（可选）
}

// 自然语言查询响应
export interface NL2QueryResult {
  buildings: string[] // 建筑 ID 列表
  parameter: string // 参数类型
  timeRange: [number, number] // 时间范围
  confidence: number // 置信度
}

export interface NL2QueryResponse {
  code: number
  message: string
  data: NL2QueryResult
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

// 查询结果数据项
export interface QueryDataItem {
  id: string
  time: string // 时间
  buildingId: string // 建筑 ID
  buildingName: string // 建筑名称
  parameterName: string // 参数名称
  value: number // 数值
  unit: string // 单位
  isAnomaly?: boolean // 是否异常
}

// 查询响应
export interface QueryResponse {
  code: number
  message: string
  data: {
    list: QueryDataItem[] // 数据列表
    total: number // 总数
    metrics: {
      totalEnergy: number // 总能耗
      avgEnergy: number // 平均能耗
      anomalyCount: number // 异常点数
    }
  }
}

// 导出参数
export interface ExportParams {
  buildings: string[]
  parameter: string
  startTime: number
  endTime: number
  format?: 'excel' | 'csv' | 'pdf' // 导出格式
}
