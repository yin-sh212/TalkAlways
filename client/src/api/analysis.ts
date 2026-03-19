import http from './http'
import type { ApiResponse } from '@/types/user'

// 洞察项类型
export interface InsightItem {
  title: string
  description: string
  category: string
  type: 'warning' | 'info' | 'success' | 'default' | 'error' | 'primary'
  color: string
}

// 异常摘要类型
export interface AnomalySummary {
  type: string
  description: string
  factors: string
  impact: string
  suggestion: string
}

// 分析响应类型
export interface AnalysisResponse {
  insights: InsightItem[]
  anomaly: AnomalySummary
}

// 获取能耗分析洞察
export const getAnalysisInsights = (params: { 
  building_id: string
  days: number
  end_date?: string
}) => {
  return http.get<ApiResponse<AnalysisResponse>>('/analysis/insights', { params })
}

import type { 
  QueryParams, 
  NL2QueryParams, 
  StatisticsParams,
  AnomalyCountParams,
} from '../types/analysis'

// 上传文件到知识库
export const uploadDocument = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  
  return http.post<any>('/upload/document', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 下载上传模板
export const downloadTemplate = () => {
  return http.get('/admin/upload/template', {
   responseType: 'blob'
  })
}

// 获取建筑列表
export const getBuildings = () => {
  return http.get('/query/buildings')
}

// 数据查询 - 使用 POST /api/query/query
export const queryData = (data: {
  building_id: string
  parameter: string
  start_date: string
  end_date: string
  time_unit?: string
}) => {
  return http.post('/query/query', data)
}

// 获取原始数据
export const getRawData = (params: { 
  building_id?: string
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}) => {
  return http.get('/query/raw', { params })
}

// 获取趋势图数据
export const getTrendData = (params: {
  building_id?: string
  days?: number
  start_date?: string
  end_date?: string
}) => {
  return http.get('/charts/trend', { params })
}

// 获取对比图数据
export const getComparisonData = (params: {
  building_ids?: string[]
  start_date?: string
  end_date?: string
}) => {
  return http.get('/charts/comparison', { params })
}

// 获取分布图数据
export const getDistributionData = (params: {
  building_id?: string
  date?: string
}) => {
  return http.get('/charts/distribution', { params })
}

// 统计摘要 - 总能耗、平均能耗
export const getStatisticsSummary = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  time_unit?: string
}) => {
  return http.get('/statistics/summary', { params })
}

// 异常检测
export const detectAnomaly = (params: {
  building_id?: string
  start_date?: string
  end_date?: string
  threshold?: number
}) => {
  return http.get('/statistics/anomaly', { params })
}

// 自然语言查询解析 - 对接智能问答接口
export const parseNaturalQuery = (params: NL2QueryParams) => {
  return http.post('/chat/ask', {
    query: params.query,
    building_id: params.context?.building_id || 'B001',
    session_id: params.context?.session_id
  })
}

// 导出报表 - 支持多种格式
export interface ExportParams {
  buildings: string[]
  startTime: string | Date
  endTime: string | Date
  format?: 'csv' | 'excel' | 'pdf'
}

export const exportCSV = (params: ExportParams) => {
  // 确保使用从后端获取的真实建筑 ID
  if (!params.buildings || params.buildings.length === 0) {
    throw new Error('必须指定建筑 ID')
  }
  
  return http.get('/export/csv', {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

export const exportExcel = (params: ExportParams) => {
  // 确保使用从后端获取的真实建筑 ID
  if (!params.buildings || params.buildings.length === 0) {
    throw new Error('必须指定建筑 ID')
  }
  
  return http.get('/export/excel', {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}

export const exportPDF = (params: ExportParams) => {
  // 确保使用从后端获取的真实建筑 ID
  if (!params.buildings || params.buildings.length === 0) {
    throw new Error('必须指定建筑 ID')
  }
  
  return http.get('/export/pdf', {
    params: {
      building_id: params.buildings[0],
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}
