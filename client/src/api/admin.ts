import http from './http'
import type { UploadHistory, CSVTemplates } from '@/types/admin'
import type { ApiResponse } from '@/types/user'

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

// 获取上传历史 - 使用 UploadHistory 类型
export const getUploadHistory = () => {
  return http.get<ApiResponse<UploadHistory[]>>('/admin/upload/history')
}

// 获取支持的 CSV 模板 - 使用 CSVTemplates 类型
export const getCSVTemplates = () => {
  return http.get<ApiResponse<CSVTemplates>>('/admin/supported-formats')
}

// 下载 CSV 模板
export const downloadCSVTemplate = (templateName: string): Promise<Blob> => {
  return http.get(`/admin/csv-template/${templateName}`, {
    responseType: 'blob'
  })
}

// 获取知识库文档列表
export interface KnowledgeDocument {
  id: number
  title: string
  category: string
  tags: string[]
  summary: string
  created_at: string
  updated_at: string
  views: number
}

export interface KnowledgeListData {
  total: number
  page: number
  page_size: number
  items: KnowledgeDocument[]
}

export const getKnowledgeList = (params?: { 
  page?: number
  page_size?: number
  category?: string
  keyword?: string
  tag?: string
}) => {
  return http.get<ApiResponse<KnowledgeListData>>('/admin/knowledge/list', { params })
}

// 获取知识库文档详情
export interface KnowledgeDetailResponse {
  code: number
  message: string
  data: KnowledgeDocument & {
    description: string
    solution: string
    notes: string
  }
}

export const getKnowledgeDetail = (docId: number) => {
  return http.get<ApiResponse<KnowledgeDetailResponse>>(`/admin/knowledge/detail/${docId}`)
}

// 添加文档到知识库
export interface AddDocumentParams {
  title: string
  category: string
  tags: string[]
  summary: string
  description: string
  solution: string
  notes: string[]
}

export const addDocument = (data: AddDocumentParams) => {
  return http.post<ApiResponse<{ id: number }>>('/admin/knowledge/add', data)
}

// 删除知识库文档
export interface DeleteDocumentResponse {
  is_success: boolean
}

export const deleteKnowledgeDocument = (docId: number) => {
  return http.delete<ApiResponse<DeleteDocumentResponse>>(`/admin/knowledge/${docId}`)
}
