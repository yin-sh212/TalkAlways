// 设备类型（后端返回的格式）
export interface DeviceResponse {
  deviceName: string
  deviceType: string
  building: string
  deviceStatus: string
  deviceTotal?: number
}

// 设备类型（前端使用的格式）
export interface Device {
  id: string
  name: string
  type: string
  building_id: string
  status: string
  created_at?: string
  updated_at?: string
}

// 设备列表响应
export interface DeviceListResponse {
  total: number
  items: DeviceResponse[]
}

// 设备统计数据
export interface DeviceStats {
  online_rate: number
  total_devices: number
  online_devices: number
  status_stats: Record<string, number>
  type_stats: Array<{
    type: string
    count: number
    percentage: number
  }>
}

// 通用 API 响应
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}