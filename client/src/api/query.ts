import http from './http'
import type { 
  RawData, 
  Building, 
  Meter, 
  DeviceStatus,
  QueryParams,
} from '@/types/query'
import type { ApiResponse } from '@/types/user'

// 获取原始能耗数据 - 使用 RawData 类型
export const getRawData = (params: QueryParams) => {
  return http.get<ApiResponse<RawData[]>>('/query/raw', { params })
}

// 获取建筑列表 - 使用 Building 类型
export const getBuildings = () => {
  return http.get<ApiResponse<Building[]>>('/query/buildings')
}

// 获取监测点列表 - 使用 Meter 类型
export const getMeters = (building_id?: string) => {
  return http.get<ApiResponse<Meter[]>>('/query/meters', { params: { building_id } })
}

// 获取设备状态 - 使用 DeviceStatus 类型
export const getDeviceStatus = (building_id?: string) => {
  return http.get<ApiResponse<DeviceStatus[]>>('/query/device-status', { params: { building_id } })
}

// 查询数据 - 使用 QueryParams 类型
export const queryData = (params: QueryParams) => {
  return http.post('/query/query', params)
}
