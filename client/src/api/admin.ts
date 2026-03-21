import http from './http'
import type { ApiResponse } from '@/types/user'

// 上传CSV文件
export const uploadCSV = (data: FormData) => {
  return http.post('/admin/upload', data, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 下载 CSV 模板
export const downloadTemplate = () => {
  return http.get('/admin/upload/template', {
    responseType: 'blob'
  })
}

// 获取上传历史
export const getUploadHistory = () => {
  return http.get('/admin/upload/history')
}

// 获取支持的文件格式
export const getSupportedFormats = () => {
  return http.get('/admin/supported-formats')
}

// ========== 知识库管理接口 ==========

// 新增文档参数
export interface AddDocumentParams {
  title: string
  category: string
  tags: string[]
  summary: string
  description: string
  solution: string
  notes: string[]
}

// 新增文档到知识库
export const addDocument = (data: AddDocumentParams) => {
  return http.post('/admin/knowledge/add', data)
}

// 获取知识库文档列表
export interface KnowledgeListParams {
  category?: string
  tag?: string
  search?: string
}

export interface KnowledgeDocument {
  id: string
  title: string
  category: string
  tags: string[]
  summary: string
  description?: string
  solution?: string
  notes?: string[]
  createDate: string
  views: number
}

export interface KnowledgeListData {
  list: KnowledgeDocument[]
  total: number
}

export const getKnowledgeList = (params?: KnowledgeListParams) => {
  return http.get<ApiResponse<KnowledgeListData>>('/admin/knowledge/list', { params })
}

// 获取知识库文档详情
export interface KnowledgeDetailResponse extends KnowledgeDocument {
  description: string
  solution: string
  notes: string[]
}

export const getKnowledgeDetail = (docId: string) => {
  return http.get<ApiResponse<KnowledgeDetailResponse>>(`/admin/knowledge/detail/${docId}`)
}

// 删除知识库文档
export const deleteKnowledgeDocument = (docId: string) => {
  return http.delete<ApiResponse<{ success: boolean; document_id: string; title: string; message: string }>>(
    `/admin/knowledge/delete/${docId}`
  )
}
