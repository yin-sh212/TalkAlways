// 智能问答相关类型定义

// ML 模型配置
export interface MLModelConfig {
  model_type: 'anomaly_detection' | 'forecasting' | 'classification'
  parameters: {
    [key: string]: any
  }
}

// 模型状态
export interface ModelStatus {
  status: 'running' | 'stopped' | 'error'
  model_type: string
  last_updated: string
  metrics: {
    [key: string]: any
  }
}

// 问答请求
export interface AskRequest {
  query: string
  session_id?: string
  context?: {
    [key: string]: any
  }
}

// 问答响应
export interface AskResponse {
  answer: string
  confidence: number
  sources: Array<{
    id: string
    title: string
    snippet: string
  }>
  session_id: string
}

// 对话消息
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

// 会话历史
export interface ChatHistory {
  session_id: string
  messages: ChatMessage[]
}
