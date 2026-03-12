// 统计分析相关类型定义

// 时段汇总数据
export interface SummaryData {
  total_elec: number
  avg_elec: number
  peak_elec: number
  total_hvac: number
  avg_hvac: number
  peak_hvac: number
  // ... 其他汇总数据字段
}

// 能效比(COP)计算结果
export interface COPResult {
  cop_value: number
  cooling_capacity: number
  input_power: number
  efficiency_level: string
  // ... 其他COP相关字段
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