// 智能问答相关类型定义

// ML模型配置
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