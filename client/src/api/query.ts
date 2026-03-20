import http from './http'
import type { ApiResponse } from '@/types/user'

// 获取原始能耗数据
export const getRawData = (params: { building_id?: string; start_date?: string; end_date?: string; limit?: number; offset?: number }) => {
  return http.get<ApiResponse<any>>('/query/raw', { params })
}

// 获取建筑列表
export const getBuildings = () => {
  return http.get<ApiResponse<any[]>>('/query/buildings')
}

// 获取监测点列表
export const getMeters = (building_id?: string) => {
  return http.get<ApiResponse<any[]>>('/query/meters', { params: { building_id } })
}

// 获取设备状态
export const getDeviceStatus = (building_id?: string) => {
  return http.get<ApiResponse<{ totalCount: number; normalCount: number; abnormalCount: number; offlineCount: number; healthScore: number }>>('/query/device-status', { params: { building_id } })
}

// 查询数据
export const queryData = (data: any) => {
  return http.post<ApiResponse<any>>('/query/query', data)
}
