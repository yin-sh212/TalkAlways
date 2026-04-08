import axios from 'axios'
import { resolveApiUrl } from './base'

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
export const saveToKnowledge = async (data: SaveToKnowledgeRequest): Promise<{ success: boolean; documentId: number }> => {
  try {
    // 先调用 create 接口保存
    const response = await axios.post(resolveApiUrl('/knowledge/create'), data)
    
    if (response.data.code === 200) {
      // 后端没有返回 ID，我们需要查询最新的一条记录
      // 通过标题和创建时间获取刚创建的文档 ID
      const listResponse = await axios.get(resolveApiUrl('/knowledge/list'), {
        params: {
          search: data.title,
          page: 1,
          page_size: 1
        }
      })
      
      if (listResponse.data.code === 200 && listResponse.data.data.list?.length > 0) {
        const newDoc = listResponse.data.data.list[0]
        return {
          success: true,
          documentId: newDoc.id
        }
      }
      
      return {
        success: true,
        documentId: 0
      }
    } else {
      throw new Error(response.data.message || '保存失败')
    }
  } catch (error: any) {
    console.error('[Knowledge] 保存失败:', error)
    throw error
  }
}

/**
 * 获取知识库文档列表
 */
export const getKnowledgeDocuments = async (params?: {
  category?: string
  tag?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<KnowledgeDocument[]> => {
  try {
    const response = await axios.get(resolveApiUrl('/knowledge/list'), { params })
    
    if (response.data.code === 200) {
      return response.data.data.list || []
    } else {
      return []
    }
  } catch (error: any) {
    console.error('[Knowledge] 获取列表失败:', error)
    return []
  }
}

/**
 * 获取文档详情
 */
export const getDocumentDetail = async (docId: number | string): Promise<KnowledgeDocument | null> => {
  try {
    const response = await axios.get(resolveApiUrl(`/knowledge/${docId}`))
    
    if (response.data.code === 200) {
      return response.data.data
    } else {
      return null
    }
  } catch (error: any) {
    console.error('[Knowledge] 获取详情失败:', error)
    return null
  }
}
