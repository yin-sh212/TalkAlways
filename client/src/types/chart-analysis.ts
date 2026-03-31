// 图表 AI 分析相关类型定义

// 图表类型
export type ChartType = 'line' | 'bar' | 'pie' | 'radar' | 'scatter' | 'area'

// 分析类型
export type AnalysisType = 'summary' | 'trend' | 'anomaly' | 'comparison'

// 图表分析请求
export interface ChartAnalysisRequest {
  // 图表基本信息
  chartType: ChartType
  chartTitle: string
  chartId?: string
  
  // 坐标轴数据
  xAxis?: string[]
  yAxisLabel?: string
  
  // 系列数据
  series: Array<{
    name: string
    data: number[]
    type?: string
    unit?: string
    color?: string
  }>
  
  // 分析配置
  analysisType?: AnalysisType
  customPrompt?: string
  timeRange?: {
    start: string
    end: string
  }
  
  // 上下文信息
  context?: {
    buildingId?: number
    buildingName?: string
    meterIds?: number[]
    energyType?: 'electricity' | 'water' | 'gas'
  }
}

// 图表分析响应
export interface ChartAnalysisResponse {
  success: boolean
  data?: {
    analysisText: string
    keyFindings?: string[]
    suggestions?: string[]
    confidence?: number
    analysisTime?: number
  }
  error?: string
}

// SSE 消息类型
export interface SSEMessage {
  type: 'status' | 'result' | 'done' | 'error'
  data: {
    message?: string
    content?: string
    progress?: number
  }
}
