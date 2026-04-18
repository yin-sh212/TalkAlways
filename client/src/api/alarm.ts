import http from './http'
import type { ApiResponse } from '@/types/user'
import type { Building, DeviceStatus } from '@/types/query'

// 获取建筑列表 - 使用 Building 类型
export const getBuildings = () => {
  return http.get<ApiResponse<Building[]>>('/query/buildings')
}

// 获取设备状态 - 使用 DeviceStatus 类型
export const getDeviceStatus = (params?: {
  building_id?: string
}) => {
  return http.get<ApiResponse<DeviceStatus[]>>('/query/device-status', { params })
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
  message: string
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

// 获取告警趋势数据 - 使用新的告警专用接口
export const getAlarmTrend = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  alarm_level?: string  // 支持逗号分隔的多值，如 "1,2,3"
  alarm_type?: string   // 支持逗号分隔的多值，如 "energy,temperature"
}) => {
  return http.get('/charts/alarm-trend', { params })
}

// 获取告警分布数据 - 使用 DistributionData 类型
export const getAlarmDistribution = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  alarm_level?: string  // 支持逗号分隔的多值
  alarm_type?: string   // 支持逗号分隔的多值
}) => {
  return http.get('/charts/distribution', { params })
}

// 获取异常检测数据 - 使用 AnomalyDetection 类型
export const detectAnomaly = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  threshold?: number
}) => {
  return http.get('/statistics/anomaly', { params })
}

// 使用真实算法生成告警 - 动态基线 + 趋势下降（新接口）
export const generateRealAlarms = (params: {
  start_date: string
  end_date: string
  building_ids?: string
  metric?: 'electricity' | 'cooling_load' | 'heating_load'
  dynamic_window?: number
  dynamic_threshold?: number
  trend_window?: number
  min_trend_decline?: number
}) => {
  return http.post('/alarm/generate-real-alarms', null, { params })
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

// 导出告警报表 - 使用 ExportParams 类型
export interface ExportParams {
  building_ids: string[]
  startTime: string | Date
  endTime: string | Date
  format?: 'csv' | 'excel' | 'pdf'
}

export const exportCSV = (params: ExportParams): Promise<Blob> => {
  return http.get('/export/csv', {
    params: {
      building_ids: params.building_ids.join(','),
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

export const exportExcel = (params: ExportParams): Promise<any> => {
  return http.get('/export/excel', {
    params: {
      building_ids: params.building_ids.join(','),
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

export const exportPDF = (params: ExportParams): Promise<any> => {
  return http.get('/export/pdf', {
    params: {
      building_ids: params.building_ids.join(','),
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

// ========== 新增告警管理接口 ==========

// 告警类型字典响应
export interface AlarmTypeDict {
  code: string
  name: string
  description: string
}

// 告警级别字典响应
export interface AlarmLevelDict {
  level: number
  name: string
  color: string
  description?: string
}

// 告警列表请求参数
export interface AlarmListParams {
  status?: string
  building_id?: string
  alarm_level?: number
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

// 告警列表响应数据
export interface AlarmListResponse {
  code: number
  message: string
  data: {
    total: number
    page: number
    page_size: number
    items: AlarmListItem[]
  }
}

// 告警列表项
export interface AlarmListItem {
  id: number
  building_id: string
  meter_id?: string
  alarm_type: string
  alarm_level: number
  description?: string
  start_time: string
  end_time?: string
  status: string
  value?: number
  threshold?: number
  solution?: string
}

// 批量操作请求
export interface BatchOperationRequest {
  alarm_ids: number[]
  resolution?: string
}

// 批量操作响应
export interface BatchOperationResponse {
  code: number
  message: string
  data: {
    confirmed_count?: number
    resolved_count?: number
    knowledge_synced_count?: number
    failed_ids: number[]
  }
}

// 获取告警类型字典
export const getAlarmTypes = () => {
  return http.get<{ code: number; message: string; data: AlarmTypeDict[] }>('/alarm/dict/alarm-types')
}

// 获取告警级别字典
export const getAlarmLevels = () => {
  return http.get<{ code: number; message: string; data: AlarmLevelDict[] }>('/alarm/dict/alarm-levels')
}

// 获取告警列表 - 使用 AlarmListParams 和 AlarmListResponse 类型
export const getAlarmList = (params?: AlarmListParams) => {
  return http.get<AlarmListResponse>('/alarm/list', { params })
}

// 获取告警统计指标
export interface AlarmStatsResponse {
  code: number
  message: string
  data: {
    totalAlarms: number
    unresolvedCount: number
    criticalCount: number
    acknowledgedCount: number
  }
}

export const getAlarmStats = (params?: {
  building_id?: string
  start_date?: string
  end_date?: string
  alarm_level?: string  // 支持逗号分隔的多值，如 "1,2,3"
  alarm_type?: string   // 支持逗号分隔的多值
}) => {
  return http.get<AlarmStatsResponse>('/alarm/stats', { params })
}

// 批量确认告警 - 使用 BatchOperationRequest 和 BatchOperationResponse 类型
export const batchConfirmAlarms = (data: BatchOperationRequest) => {
  return http.post<BatchOperationResponse>('/alarm/batch-confirm', data)
}

// 批量解决告警 - 使用 BatchOperationRequest 和 BatchOperationResponse 类型
export const batchResolveAlarms = (data: BatchOperationRequest) => {
  return http.post<BatchOperationResponse>('/alarm/batch-resolve', data)
}

// 获取告警分析详情
export interface AlarmAnalysisResponse {
  code: number
  message: string
  data: {
    alarm_id: number
    building_id: string
    alarm_type: string
    alarm_level: number
    description: string
    start_time: string
    main_cause: string
    top_factors: Array<{
      factor: string
      value: number
      normal?: number
      impact: 'high' | 'medium' | 'low'
      description: string
    }>
    quick_solution: string
    related_knowledge?: Array<{
      title: string
      url: string
    }>
  }
}

export const getAlarmAnalysis = (alarmId: number) => {
  return http.get<AlarmAnalysisResponse>(`/alarm/${alarmId}/analysis`)
}
