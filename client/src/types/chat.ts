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

// 引用来源（后端 rag_answer.to_sources 产出：{id, title, snippet}）
export interface SourceRef {
  id: string
  title: string
  snippet: string
}

// 问答响应
export interface AskResponse {
  answer: string
  confidence: number
  // 后端返回 mode: 'rag'（命中语料）| 'llm'（未命中，走降级）
  mode?: string
  sources: SourceRef[]
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
