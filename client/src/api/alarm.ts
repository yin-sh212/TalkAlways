import http from './http'

// 获取建筑列表
export const getBuildings = () => {
  return http.get('/query/buildings')
}

// 获取设备状态
export const getDeviceStatus = (params?: {
  building_id?: string
}) => {
  return http.get('/query/device-status', { params })
}

// 告警查询参数
export interface AlarmQueryParams {
  building_ids?: string[]
  severity?: string[]
  alarm_type?: string[]
  start_date?: string
  end_date?: string
  status?: string[]
  page?: number
  page_size?: number
}

// 告警查询响应
export interface AlarmResponse {
  code: number
  data: {
    alarms: AlarmItem[]
    total: number
  }
}

export interface AlarmItem {
  id: string
  timestamp: string
  building_id: string
  building_name: string
  device_id?: string
  device_name?: string
  alarm_type: string
  severity: string
  status: 'unresolved' | 'acknowledged' | 'resolved'
  description: string
  value?: number
  threshold?: number
}

// 告警查询 - 使用 POST /api/query/query
export const queryAlarms = (data: AlarmQueryParams) => {
  return http.post<AlarmResponse>('/query/query', data)
}

// 获取告警统计摘要
export const getAlarmSummary = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  time_unit?: string
}) => {
  return http.get('/statistics/summary', { params })
}

// 获取告警趋势数据
export const getAlarmTrend = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
}) => {
  return http.get('/charts/trend', { params })
}

// 获取告警分布数据
export const getAlarmDistribution = (params: {
  building_id?: string
  date?: string
}) => {
  return http.get('/charts/distribution', { params })
}

// 获取异常检测数据
export const detectAnomaly = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  threshold?: number
}) => {
  return http.get('/statistics/anomaly', { params })
}

// 确认告警（单个）
export const acknowledgeAlarm = (data: {
  alarm_id: string
  operator?: string
}) => {
  return http.post('/query/query', {
    action: 'acknowledge',
    alarm_id: data.alarm_id,
    operator: data.operator
  })
}

// 解决告警（单个）
export const resolveAlarm = (data: {
  alarm_id: string
  operator?: string
  resolution?: string
}) => {
  return http.post('/query/query', {
    action: 'resolve',
    alarm_id: data.alarm_id,
    operator: data.operator,
    resolution: data.resolution
  })
}

// 批量确认告警
export const batchAcknowledge = (data: {
  alarm_ids: string[]
  operator?: string
}) => {
  return http.post('/query/query', {
    action: 'batch_acknowledge',
    alarm_ids: data.alarm_ids,
    operator: data.operator
  })
}

// 批量解决告警
export const batchResolve = (data: {
  alarm_ids: string[]
  operator?: string
  resolution?: string
}) => {
  return http.post('/query/query', {
    action: 'batch_resolve',
    alarm_ids: data.alarm_ids,
    operator: data.operator,
    resolution: data.resolution
  })
}

// 导出告警报表
export interface ExportParams {
  building_ids: string[]
  startTime: string | Date
  endTime: string | Date
  format?: 'csv' | 'excel' | 'pdf'
}

export const exportCSV = (params: ExportParams) => {
  return http.get('/export/csv', {
    params: {
      building_id: params.building_ids[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

export const exportExcel = (params: ExportParams) => {
  return http.get('/export/excel', {
    params: {
      building_id: params.building_ids[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

export const exportPDF = (params: ExportParams) => {
  return http.get('/export/pdf', {
    params: {
      building_id: params.building_ids[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}