// 数据查询相关类型定义

// 原始能耗数据
export interface RawData {
  id: string
  timestamp: string
  building_id: string
  meter_id: string
  electricity: number
  hvac: number
  water: number
  // ... 其他能耗数据字段
}

// 建筑信息
export interface Building {
  id: string
  name: string
  type: string
  area: number
  // ... 其他建筑属性
}

// 监测点信息
export interface Meter {
  id: string
  name: string
  type: string
  location: string
  building_id: string
  // ... 其他监测点属性
}

// 设备状态
export interface DeviceStatus {
  id: string
  name: string
  status: 'running' | 'standby' | 'fault' | 'maintenance'
  last_update: string
  // ... 其他设备状态属性
}

// 查询参数
export interface QueryParams {
  building_id?: string
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}