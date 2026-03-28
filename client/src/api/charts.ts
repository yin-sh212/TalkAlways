import http from './http'
import type { 
  TrendData, 
  ComparisonData, 
  DistributionData,
  TrendParams
} from '@/types/charts'
import type { ApiResponse } from '@/types/user'

// 获取趋势图数据 - 使用 TrendData 类型
export const getTrendData = (params: TrendParams) => {
  return http.get<ApiResponse<TrendData>>('/charts/trend', { params })
}

// 获取对比图数据 - 使用 ComparisonData 类型
export const getComparisonData = (params: {
  building_ids?: string | string[]
  start_date?: string
  end_date?: string
}) => {
  return http.get<ApiResponse<ComparisonData>>('/charts/comparison', { params })
}

// 获取分布图数据 - 使用 DistributionData 类型
export const getDistributionData = (params: {
  building_id?: string
  date?: string
}) => {
  return http.get<ApiResponse<DistributionData>>('/charts/distribution', { params })
}

// 获取能耗分布数据 - 使用 TrendData 类型（复用趋势图数据结构）
export const getEnergyDistributionData = (params: {
  building_id?: string
  date?: string
}) => {
  return http.get<ApiResponse<TrendData>>('/charts/energy-distribution', { params })
}
