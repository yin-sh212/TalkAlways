import http from './http'

// 配置机器学习模型
export const configureMLModel = (data: { model_type: string; parameters: any }) => {
  return http.post('/chat/configure-ml-model', data)
}

// 获取模型状态
export const getModelStatus = () => {
  return http.get('/chat/model-status')
}

// 智能问答 - 入参只有用户输入的文字
export const askQuestion = (query: string) => {
  return http.post('/chat/ask', { query })
}

// 健康检查
export const checkHealth = () => {
  return http.get('/chat/health')
}
