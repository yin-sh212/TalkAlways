import http from './http'
import type { 
  SummaryData, 
  COPResult, 
  AnomalyDetection,
  SummaryParams,
  StatisticsResponse
} from '@/types/statistics'
import type { ApiResponse } from '@/types/user'

// 获取时段汇总 - 使用 SummaryData 类型
export interface SummaryResponse extends SummaryData {
  building_id: string
  period: string
  time_unit: string
  details: any[]
}

export const getSummary = (params: SummaryParams) => {
  return http.get<ApiResponse<SummaryResponse>>('/statistics/summary', { params })
}

// 批量获取多个建筑的能耗汇总 - 用于建筑能耗对比
export interface BuildingSummaryItem {
  period: string
  building_id: string
  building_name: string
  total_elec: number
  avg_elec: number
  data_points: number
}

export interface BuildingsSummaryResponse {
  buildings: BuildingSummaryItem[]
}

export const getBuildingsSummary = (params: { 
  start_date: string
  end_date: string
  time_unit?: string
  building_ids?: string[]
}) => {
  return http.get<ApiResponse<BuildingsSummaryResponse>>('/statistics/summary/buildings', { params })
}

// 批量获取多日的能耗数据 - 用于日环比、周同比计算
export interface DailyComparisonItem {
  date: string
  total_elec: number
  avg_elec: number
  data_points: number
}

export interface DailyComparisonResponse {
  daily_data: DailyComparisonItem[]
}

export const getDailyComparison = (params: { 
  building_id: string
  dates: string[]
}) => {
  return http.get<ApiResponse<DailyComparisonResponse>>('/statistics/summary/daily-comparison', { params })
}

// 计算能效比 (COP) - 使用 COPResult 类型
export interface COPResponse extends COPResult {
  building_id: string
  period: string
  cop_type: string
  details: any[]
}

export const calculateCOP = (params: { 
  building_id?: string
  start_date?: string
  end_date?: string
  cop_type?: string
}) => {
  return http.get<ApiResponse<COPResponse>>('/statistics/cop', { params })
}

// 检测能耗异常 - 使用 AnomalyDetection 类型
export interface AnomalyAPIResponse {
  code: number
  message: string
  data: {
    building_id: string
    period: string
    total_points: number
    anomaly_count: number
    anomalies: Array<{
      timestamp: string
      value: number
      predicted: number
      residual: number
    }>
  }
}

export const detectAnomaly = (params: { 
  building_id?: string
  start_date?: string
  end_date?: string
  threshold?: number
}) => {
  return http.get<AnomalyAPIResponse>('/statistics/anomaly', { params })
}
