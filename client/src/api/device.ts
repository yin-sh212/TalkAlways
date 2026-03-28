import http from './http'
import type { DeviceListResponse, DeviceStats, Device } from '@/types/device'
import type { ApiResponse } from '@/types/user'

// 新增设备请求参数
export interface AddDeviceRequest {
  name: string
  type: string
  building_id: string
  status?: string 
}

// 更新设备请求参数
export interface UpdateDeviceRequest {
  name?: string
  type?: string
  building_id?: string
  status?: string
}

/**
 * 获取设备列表 - 使用 DeviceListResponse 类型
 * @param deviceName 设备名称（可选，支持模糊查询）
 */
export const getDeviceList = (deviceName?: string) => {
  return http.get<ApiResponse<DeviceListResponse>>('/device/list', { 
    params: { device_name: deviceName } 
  })
}

/**
 * 新增设备 - 使用 AddDeviceRequest 类型
 * @param data 设备信息
 */
export const addDevice = (data: AddDeviceRequest) => {
  return http.post<ApiResponse<{ device_id: string; is_success: boolean }>>('/device/add', data)
}

/**
 * 更新设备信息 - 使用 UpdateDeviceRequest 类型
 * @param deviceId 设备 ID
 * @param data 更新的设备信息
 */
export const updateDevice = (deviceId: string, data: UpdateDeviceRequest) => {
  return http.put<ApiResponse<{ is_success: boolean }>>(`/device/update/${deviceId}`, data)
}

/**
 * 删除设备（软删除）
 * @param deviceId 设备 ID
 */
export const deleteDevice = (deviceId: string) => {
  return http.delete<ApiResponse<{ is_success: boolean }>>(`/device/delete/${deviceId}`)
}

/**
 * 获取设备统计数据 - 使用 DeviceStats 类型
 */
export const getDeviceStats = () => {
  return http.get<ApiResponse<DeviceStats>>('/device/stats')
}
