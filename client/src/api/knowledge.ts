import http from './http'

export interface KnowledgeDocument {
  id: number | string
  title: string
  category: string
  tags?: string[]
  summary: string
  description?: string
  solution?: string
  notes?: string[]
  views?: number
  createdAt?: string
  updatedAt?: string
}

export interface SaveToKnowledgeRequest {
  title: string
  category: string
  tags: string[]
  summary: string
  description: string
  solution: string
  notes: string[]
}

/**
 * 保存文档到知识库
 */
export const saveToKnowledge = async (data: SaveToKnowledgeRequest) => {
  return http.post('/knowledge/save', data)
}

/**
 * 获取知识库文档列表
 */
export const getKnowledgeList = async (params?: {
  category?: string
  keyword?: string
  page?: number
  pageSize?: number
}) => {
  return http.get('/knowledge/list', { params })
}

/**
 * 获取知识库文档详情
 */
export const getKnowledgeDetail = async (id: string | number) => {
  return http.get(`/knowledge/${id}`)
}

/**
 * 删除知识库文档
 */
export const deleteKnowledge = async (id: string | number) => {
  return http.delete(`/knowledge/${id}`)
}

/**
 * 搜索知识库
 */
export const searchKnowledge = async (keyword: string) => {
  return http.get('/knowledge/search', { params: { keyword } })
}