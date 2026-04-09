import http from './http'
import type { 
  MLModelConfig, 
  ModelStatus, 
  AskRequest, 
  AskResponse,
  ChatMessage,
  ChatHistory
} from '@/types/chat'
import type { ApiResponse } from '@/types/user'

// 配置机器学习模型 - 使用 MLModelConfig 类型
export const configureMLModel = (config: MLModelConfig) => {
  return http.post<ApiResponse<{ success: boolean }>>('/chat/configure-ml-model', config)
}

// 获取模型状态 - 使用 ModelStatus 类型
export const getModelStatus = () => {
  return http.get<ApiResponse<ModelStatus>>('/chat/model-status')
}

// 智能问答 - 普通模式（一次性返回）- 使用 AskRequest 和 AskResponse 类型
export const askQuestion = (query: string) => {
  const params: AskRequest = { query }
  return http.post<ApiResponse<AskResponse>>('/chat/ask', params)
}

// 智能问答 - 流式模式(逐字输出)
export const askQuestionStream = (query: string, onChunk: (chunk: string) => void) => {
  const controller = new AbortController()
  
  // 开发环境使用相对路径,通过 Vite 代理转发
  const streamUrl = '/api/chat/ask/stream'
  
  const fetchPromise = fetch(streamUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query } as AskRequest),
    signal: controller.signal,
  })
  
  fetchPromise.then(async (response) => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Readable stream not supported')
    }
    
    const decoder = new TextDecoder()
    
    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          break
        }
        
        const chunk = decoder.decode(value, { stream: true })
        // 解析 SSE 格式的数据
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data !== '[DONE]') {
              try {
                // 解析 JSON 并提取 content 字段
                const parsed = JSON.parse(data)
                if (parsed.data?.content) {
                  onChunk(parsed.data.content)
                }
              } catch (e) {
                console.error('解析 SSE 数据失败:', e)
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }).catch((error) => {
    console.error('流式请求失败:', error)
    throw error
  })
  
  return controller
}

// 获取会话历史 - 使用 ChatHistory 类型
export const getChatHistory = (sessionId?: string) => {
  return http.get<ApiResponse<ChatHistory>>('/chat/history', { 
    params: { session_id: sessionId } 
  })
}

// 清除会话历史
export const clearChatHistory = (sessionId: string) => {
  return http.delete<ApiResponse<{ success: boolean }>>(`/chat/history/${sessionId}`)
}

// 健康检查
export const checkHealth = () => {
  return http.get<ApiResponse<{ status: string; timestamp: string }>>('/chat/health')
}
