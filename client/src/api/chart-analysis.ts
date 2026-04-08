import type { ChartAnalysisRequest, SSEMessage } from '@/types/chart-analysis'
import { resolveApiUrl } from './base'

/**
 * 使用 SSE 流式分析图表
 * @param chartData 请求数据
 * @param onStream 消息回调
 * @param signal AbortSignal 用于取消请求
 * @returns Promise 用于等待完成或捕获错误
 */
export const analyzeChartWithAIStream = (
  chartData: ChartAnalysisRequest,
  onStream: (message: SSEMessage) => void,
  signal?: AbortSignal
): Promise<void> => {
  return new Promise(async (resolve, reject) => {
    try {
      const controller = new AbortController()
      
      // 如果传入了 signal，监听取消事件
      if (signal) {
        signal.addEventListener('abort', () => {
          controller.abort()
          reject(new Error('分析已取消'))
        })
      }
      
      // 设置超时
      const timeoutId = setTimeout(() => {
        controller.abort()
        reject(new Error('请求超时，请重试'))
      }, 60000) // 60 秒超时
      
      const response = await fetch(resolveApiUrl('/chart/analyze/stream'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(chartData),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法获取响应流')
      }
      
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          break
        }
        
        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk
        
        // 解析 SSE 消息
        const lines = buffer.split('\n')
        buffer = '' // 清空缓冲区
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              // 根据消息类型回调
              if (data.type === 'status' || 
                  data.type === 'result' || 
                  data.type === 'done' || 
                  data.type === 'error') {
                onStream(data as SSEMessage)
              } else {
                // 兼容旧格式
                onStream({
                  type: 'result',
                  data: data
                })
              }
              
              // 如果是 done 消息，结束
              if (data.type === 'done') {
                resolve()
                return
              }
            } catch (e) {
              console.warn('[Chart AI] 解析 SSE 消息失败:', e, line)
            }
          }
        }
      }
      
      resolve()
    } catch (error: any) {
      console.error('[Chart AI] 流式分析失败:', error)
      onStream({
        type: 'error',
        data: {
          message: error.message || '分析失败，请稍后重试'
        }
      })
      reject(error)
    }
  })
}
