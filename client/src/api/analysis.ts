import http from './http'
import type { 
  QueryParams, 
  QueryResponse, 
  NL2QueryParams, 
  NL2QueryResponse, 
  ExportParams,
  StatisticsParams,
  StatisticsResponse,
  AnomalyCountParams,
  AnomalyCountResponse
} from '../types/analysis'

// 自然语言查询解析 - 对接智能问答接口
export const parseNaturalQuery = (params: NL2QueryParams) => {
  // 后端接口：POST /api/chat/ask
  return http.post('/chat/ask', {
    query: params.query,
    building_id: params.context?.building_id || 'B001',
    session_id: params.context?.session_id
  })
}

// 数据查询 - 原始数据
export const queryData = (params: QueryParams) => {
  // 后端接口：GET /api/query/raw
  return http.get('/query/raw', {
    params: {
      building_id: params.buildings[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0],
      limit: params.pageSize || 100,
      offset: (params.pageNum || 1) - 1
    }
  })
}

// 统计摘要 - 总能耗、平均能耗
export const getStatisticsSummary = (params: StatisticsParams) => {
  // 后端接口：GET /api/statistics/summary
  return http.get('/statistics/summary', {
    params: {
      building_id: params.buildings[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0],
      group_by: 'day'
    }
  })
}

// 异常统计 - 异常点数
export const getAnomalyCount = (params: AnomalyCountParams) => {
  // 后端接口：GET /api/statistics/anomaly
  return http.get('/statistics/anomaly', {
    params: {
      building_id: params.buildings[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0],
      threshold: 2.0
    }
  })
}

// 导出报表 - 支持多种格式
export const exportReport = (params: ExportParams) => {
  // 后端接口：GET /api/export/{format}
  const format = params.format || 'excel'
  return http.get(`/export/${format}`, {
    params: {
      building_id: params.buildings[0] || 'B001',
      start_date: new Date(params.startTime).toISOString().split('T')[0],
      end_date: new Date(params.endTime).toISOString().split('T')[0]
    },
    responseType: 'blob'
  })
}
