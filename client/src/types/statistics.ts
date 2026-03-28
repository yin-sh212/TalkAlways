// 统计分析相关类型定义

// 时段汇总数据
export interface SummaryData {
  total_elec: number
  avg_elec: number
  peak_elec: number
  total_hvac: number
  avg_hvac: number
  peak_hvac: number
}

// 统计汇总接口返回的详细数据项
export interface StatisticsDetail {
  period: string
  data_points: number
  total_elec: number
  avg_elec: number
  max_elec: number
  min_elec: number
  std_elec: number
  total_cooling: number
  avg_cooling: number
  max_cooling: number
  min_cooling: number
  total_heating: number
  avg_heating: number
  max_heating: number
  min_heating: number
  avg_temp: number
  max_temp: number
  min_temp: number
  avg_pressure: number
}

// 统计汇总接口返回的 summary 字段
export interface StatisticsSummary {
  total_points: number
  total_elec: number
  avg_elec: number
  total_cooling: number
  avg_cooling: number
  total_heating: number
  avg_heating: number
  avg_temp: number
  avg_pressure: number
}

// 统计汇总接口完整响应（包含 summary 和 details）
export interface StatisticsSummaryResponse {
  building_id: string
  period: string
  time_unit: string
  include_fields: string
  details: StatisticsDetail[]
  summary: StatisticsSummary
}

// 能效比 (COP) 计算结果
export interface COPResult {
  avg_cop_cooling?: number | null
  avg_cop_heating?: number | null
  cop_type?: string
  evaluation?: {
    cooling?: {
      level: string
      description: string
      avg_cop?: number
    }
    heating?: {
      level: string
      description: string
      avg_cop?: number
    }
  } | null
  standard?: {
    normal_min: number
    normal_max: number
    low_min: number
    low_max: number
    abnormal_max: number
  }
  details?: any[]
}

// 异常检测结果
export interface AnomalyDetection {
  anomalies: Array<{
    id: string
    timestamp: string
    building_id: string
    metric: string
    value: number
    threshold: number
    severity: 'low' | 'medium' | 'high'
    description: string
  }>
  summary: {
    total_count: number
    high_severity_count: number
    medium_severity_count: number
    low_severity_count: number
  }
}

// 汇总查询参数
export interface SummaryParams {
  building_id?: string
  start_date?: string
  end_date?: string
  time_unit?: 'hour' | 'day' | 'week' | 'month'
}

// 统计响应
export interface StatisticsResponse<T> {
  code: number
  message: string
  data: T
}
