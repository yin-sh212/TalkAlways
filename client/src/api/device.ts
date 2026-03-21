import http from './http'
import type { DeviceListResponse, DeviceStats, ApiResponse } from '@/types/device'

/**
 * 获取设备列表
 * @param deviceName 设备名称（可选，支持模糊查询）
 */
export const getDeviceList = (deviceName?: string) => {
  return http.get<ApiResponse<DeviceListResponse>>('/device/list', { 
    params: { device_name: deviceName } 
  })
}

/**
 * 新增设备
 * @param data 设备信息
 */
export const addDevice = (data: { 
  name: string
  type: string
  building_id: string
  status?: string 
}) => {
  return http.post<ApiResponse<{ device_id: string; is_success: boolean }>>('/device/add', data)
}

/**
 * 更新设备信息
 * @param deviceId 设备 ID
 * @param data 更新的设备信息
 */
export const updateDevice = (deviceId: string, data: {
  name?: string
  type?: string
  building_id?: string
  status?: string
}) => {
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
 * 获取设备统计数据
 */
export const getDeviceStats = () => {
  return http.get<ApiResponse<DeviceStats>>('/device/stats')
}
