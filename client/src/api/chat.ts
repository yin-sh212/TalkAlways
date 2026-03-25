import http from './http'

// 配置机器学习模型
export const configureMLModel = (data: { model_type: string; parameters: any }) => {
  return http.post('/chat/configure-ml-model', data)
}

// 获取模型状态
export const getModelStatus = () => {
  return http.get('/chat/model-status')
}

// 智能问答 - 普通模式（一次性返回）
export const askQuestion = (query: string) => {
  return http.post('/chat/ask', { query })
}

// 智能问答 - 流式模式（逐字输出）
export const askQuestionStream = (query: string, onChunk: (chunk: string) => void) => {
  const controller = new AbortController()
  
  const fetchPromise = fetch('http://localhost:3000/api/chat/ask/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
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

// 健康检查
export const checkHealth = () => {
  return http.get('/chat/health')
}