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

// 计算能效比 (COP)
export const calculateCOP = (params: { building_id?: string; start_date?: string; end_date?: string }) => {
  return http.get<ApiResponse<number>>('/statistics/cop', { params })
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