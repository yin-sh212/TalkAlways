import http from './http'
import type { ApiResponse } from '@/types/user'

export interface AIAnalysisRequest {
  question: string
  context: {
    current_page?: string
    building_id?: string
    selected_date?: string
    clicked_element?: string
    [key: string]: any
  }
}

export interface AIAnalysisResponse {
  answer: string
  supporting_data: Record<string, any[]>
  suggested_questions: string[]
  visualization_type: 'bar' | 'line' | 'pie' | 'table'
  confidence: number
  reasoning: string
}

export interface Insight {
  title: string
  description: string
  category: 'hvac' | 'lighting' | 'equipment' | 'other'
  priority: 'high' | 'medium' | 'low'
  estimated_savings_kwh: number
  estimated_savings_cny: number
  action: string
}

export interface QuickInsightsResponse {
  insights: Insight[]
  priority: 'high' | 'medium' | 'low' | 'normal' | 'error'
  total_detected: number
}

/**
 * AI 智能分析接口
 * @param question 用户问题
 * @param context 页面上下文信息
 */
export const analyzeWithAI = (question: string, context: AIAnalysisRequest['context']) => {
  return http.post<ApiResponse<AIAnalysisResponse>>('/ai-analyst/analyze', {
    question,
    context
  })
}

/**
 * 快速生成推荐问题接口（用于划词分析）
 * @param selectedText 选中的文本
 * @param context 页面上下文
 */
export const generateQuickSuggestions = (selectedText: string, context: Record<string, any> = {}) => {
  return http.post<ApiResponse<{ suggestions: string[] }>>('/ai-analyst/quick-suggestions', {
    selected_text: selectedText,
    context
  })
}

/**
 * 获取快速洞察（主动推送）
 * @param building_id 建筑 ID
 */
export const getQuickInsights = (building_id: string) => {
  return http.get<ApiResponse<QuickInsightsResponse>>(`/ai-analyst/quick-insights/${building_id}`)
}

/**
 * 获取 AI 可访问的数据表信息
 */
export const getAvailableTables = () => {
  return http.get<ApiResponse<{ tables: Array<{ TABLE_NAME: string; TABLE_COMMENT: string }>; count: number }>>('/ai-analyst/tables')
}