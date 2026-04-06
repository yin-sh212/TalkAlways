import http from './http'
import type { ApiResponse } from '@/types/user'
import type { 
  QueryParams, 
  NL2QueryParams, 
  StatisticsParams,
  AnomalyCountParams,
  BuildingEnergyDetail,
  EnergySummary,
  BuildingEnergyDetailResponse,
  ExportParams as AnalysisExportParams
} from '@/types/analysis'

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

// 上传文件到知识库 - 使用 FormData
export const uploadDocument = (file: File): Promise<any> => {
  const formData = new FormData()
  formData.append('file', file)
  
  return http.post<any>('/admin/upload/document', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 下载上传模板
export const downloadTemplate = (): Promise<Blob> => {
  return http.get('/admin/upload/template', {
   responseType: 'blob'
  })
}

// 获取建筑列表 - 使用 Building 类型
export const getBuildings = (): Promise<ApiResponse<any[]>> => {
  return http.get('/query/buildings')
}

// 数据查询 - 使用 QueryParams 类型
export const queryData = (params: QueryParams): Promise<any> => {
  return http.post('/query/query', params)
}

// 获取原始数据 - 使用 RawData 类型
export const getRawData = (params: QueryParams): Promise<any> => {
  return http.get('/query/raw', { params })
}

// 获取趋势图数据 - 使用 TrendParams 类型
export const getTrendData = (params: {
  building_id?: string
  days?: number
  start_date?: string
  end_date?: string
}): Promise<any> => {
  return http.get('/charts/trend', { params })
}

// 获取对比图数据
export const getComparisonData = (params: {
  building_ids?: string | string[]
  start_date?: string
  end_date?: string
}): Promise<any> => {
  return http.get('/charts/comparison', { params })
}

// 获取分布图数据
export const getDistributionData = (params: {
  building_id?: string
  date?: string
}): Promise<any> => {
  return http.get('/charts/distribution', { params })
}

// 统计摘要 - 总能耗、平均能耗 - 使用 StatisticsParams 类型
export const getStatisticsSummary = (params: StatisticsParams): Promise<any> => {
  return http.get('/statistics/summary', { params })
}

// 异常检测 - 使用 AnomalyCountParams 类型
export const detectAnomaly = (params: AnomalyCountParams): Promise<any> => {
  return http.get('/statistics/anomaly', { params })
}

// 自然语言查询解析 - 对接智能问答接口 - 使用 NL2QueryParams 类型
export const parseNaturalQuery = (params: NL2QueryParams): Promise<any> => {
  return http.post('/chat/ask', {
    query: params.query,
    building_id: params.context?.building_id || 'B001',
    session_id: params.context?.session_id
  })
}

// 导出报表 - 使用 ExportParams 类型
export const exportCSV = (params: AnalysisExportParams): Promise<Blob> => {
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

export const exportExcel = (params: AnalysisExportParams): Promise<Blob> => {
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

export const exportPDF = (params: AnalysisExportParams): Promise<any> => {
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

// 获取建筑能耗详情 - 使用 BuildingEnergyDetail 类型
export const getBuildingEnergyDetail = async (
  params: QueryParams
): Promise<BuildingEnergyDetailResponse> => {
  const response = await http.get<BuildingEnergyDetailResponse>('/analysis/building-detail', { params })
  return response.data
}

// 获取多建筑对比数据
export const getMultiBuildingComparison = (
  params: StatisticsParams & { building_ids: string[] }
): Promise<any> => {
  return http.get('/analysis/multi-building', { params })
}
