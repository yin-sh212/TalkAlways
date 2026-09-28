import http from './http'
import type {
  MLModelConfig,
  ModelStatus,
  AskRequest,
  AskResponse,
  ChatMessage,
  ChatHistory,
  SourceRef
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
// onSources：回答结束后后端会补发一帧 {data:{sources:[...]}}（无 content 字段）。
// 该帧是**向后兼容**的追加 —— 老调用方不传 onSources 时被安全忽略。
export const askQuestionStream = async (
  query: string,
  onChunk: (chunk: string) => void,
  onSources?: (sources: SourceRef[]) => void
): Promise<void> => {
  const controller = new AbortController()

  // 开发环境使用相对路径,通过 Vite 代理转发
  const streamUrl = '/api/chat/ask/stream'
  
  try {
    const response = await fetch(streamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query } as AskRequest),
      signal: controller.signal,
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Readable stream not supported')
    }
    
    const decoder = new TextDecoder()
    // TCP 会从任意字节处切分，一个 `data: {...}` 帧可能跨两次 read()。
    // buf 保存上一轮末尾的半行，与本轮字节拼接后再按行切分；否则半行
    // （前半不以 'data: ' 开头、后半不是合法 JSON）会在两端被静默丢弃。
    let buf = ''

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        buf += decoder.decode(value, { stream: true })
        // 解析 SSE 格式的数据
        const lines = buf.split('\n')
        buf = lines.pop() ?? '' // 末段可能是半行，留到下一轮拼接
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data !== '[DONE]') {
              try {
                // 解析 JSON 并提取 content 字段
                const parsed = JSON.parse(data)
                if (parsed.data?.content) {
                  onChunk(parsed.data.content)
                } else if (parsed.data?.sources && onSources) {
                  // 引用帧：无 content 字段，只在传了回调时透传
                  onSources(parsed.data.sources)
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
  } catch (error) {
    console.error('流式请求失败:', error)
    throw error
  }
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
