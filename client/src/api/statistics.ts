import http from './http'
import type { ApiResponse } from '@/types/user'

// 获取时段汇总
export const getSummary = (params: { building_id?: string; start_date?: string; end_date?: string; time_unit?: string }) => {
  return http.get<ApiResponse<{
    building_id: string;
    period: string;
    time_unit: string;
    details: any[];
    summary: {
      total_elec: number | null;
      avg_elec: number | null;
      total_water: number | null;
    }
  }>>('/statistics/summary', { params })
}

// 批量获取多个建筑的能耗汇总 - 用于建筑能耗对比
export const getBuildingsSummary = (params: { start_date: string; end_date: string; time_unit?: string; building_ids?: string[] }) => {
  return http.get<ApiResponse<{
    buildings: Array<{
      period: string;
      building_id: string;
      building_name: string;
      total_elec: number;
      avg_elec: number;
      data_points: number;
    }>
  }>>('/statistics/summary/buildings', { params })
}

// 批量获取多日的能耗数据 - 用于日环比、周同比计算
export const getDailyComparison = (params: { building_id: string; dates: string[] }) => {
  return http.get<ApiResponse<{
    daily_data: Array<{
      date: string;
      total_elec: number;
      avg_elec: number;
      data_points: number;
    }>
  }>>('/statistics/summary/daily-comparison', { params })
}

// 计算能效比 (COP)
export const calculateCOP = (params: { building_id?: string; start_date?: string; end_date?: string; cop_type?: string }) => {
  return http.get<ApiResponse<{
    building_id: string;
    period: string;
    cop_type: string;
    avg_cop_cooling: number | null;
    avg_cop_heating: number | null;
    details: any[];
  }>>('/statistics/cop', { params })
}

// 检测能耗异常
export const detectAnomaly = (params: { building_id?: string; start_date?: string; end_date?: string; threshold?: number }) => {
  return http.get<ApiResponse<{
    building_id: string;
    period: string;
    total_points: number;
    anomaly_count: number;
    anomalies: {
      timestamp: string;
      value: number;
      predicted: number;
      residual: number;
    }[];
  }>>('/statistics/anomaly', { params })
}
