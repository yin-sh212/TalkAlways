import http from './http'
import type { QueryParams, QueryResponse, NL2QueryParams, NL2QueryResponse, ExportParams } from '@/types/analysis'

// 自然语言查询解析
export const parseNaturalQuery = (params: NL2QueryParams) => {
  return http.post<NL2QueryResponse>('/analysis/nl2query', params)
}

// 数据查询
export const queryData = (params: QueryParams) => {
  return http.post<QueryResponse>('/analysis/query', params)
}

// 导出报表
export const exportReport = (params: ExportParams) => {
  return http.post<Blob>('/analysis/export', params, {
    responseType: 'blob'
  })
}
