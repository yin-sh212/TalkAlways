// 图表数据相关类型定义

// 趋势图数据
export interface TrendData {
  categories: string[]
  series: Array<{
    name: string
    type: 'line' | 'bar'
    data: number[]
  }>
}

// 对比图数据
export interface ComparisonData {
  buildings: Array<{
    id: string
    name: string
    data: number[]
  }>
  metrics: string[]
  time_range: {
    start: string
    end: string
  }
}

// 分布图数据
export interface DistributionData {
  labels: string[]
  values: number[]
  colors?: string[]
}

// 趋势图查询参数
export interface TrendParams {
  building_id?: string
  days?: number
}