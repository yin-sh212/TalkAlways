/**
 * 图表数据提取工具
 * 从 ECharts 实例中提取结构化数据用于 AI 分析
 */
import * as echarts from 'echarts'
import type { ChartAnalysisRequest, ChartType } from '@/types/chart-analysis'

/**
 * 从 ECharts 实例中提取结构化数据
 * @param chartInstance ECharts 实例
 * @param options 额外选项
 */
export function extractChartData(
  chartInstance: echarts.ECharts | null,
  options: {
    title: string
    type?: string
  }
): ChartAnalysisRequest {
  if (!chartInstance) {
    throw new Error('图表实例不存在')
  }
  
  // 获取图表配置
  const option: any = chartInstance.getOption()
  
  // 提取基础信息
  const chartType = detectChartType(option)
  const chartTitle = options.title || extractTitle(option)
  
  // 提取坐标轴数据
  const xAxis = extractXAxisData(option)
  const yAxisLabel = extractYAxisLabel(option)
  
  // 提取系列数据
  const series = extractSeriesData(option)
  
  return {
    chartType: chartType as ChartType,
    chartTitle,
    xAxis,
    yAxisLabel,
    series,
    analysisType: 'summary'
  }
}

/**
 * 检测图表类型
 */
function detectChartType(option: any): string {
  const series = option.series || []
  if (series.length === 0) return 'line'
  
  const firstSeries = series[0]
  if (firstSeries.type === 'line') {
    // 判断是否为面积图
    return firstSeries.areaStyle ? 'area' : 'line'
  }
  if (firstSeries.type === 'bar') return 'bar'
  if (firstSeries.type === 'pie') return 'pie'
  if (firstSeries.type === 'radar') return 'radar'
  if (firstSeries.type === 'scatter') return 'scatter'
  
  return 'line' // 默认
}

/**
 * 提取标题
 */
function extractTitle(option: any): string {
  if (!option.title) return '未命名图表'
  const title = Array.isArray(option.title) ? option.title[0] : option.title
  return typeof title.text === 'string' ? title.text : '未命名图表'
}

/**
 * 提取 X 轴数据
 */
function extractXAxisData(option: any): string[] {
  if (!option.xAxis) return []
  
  const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis
  return xAxis?.data || []
}

/**
 * 提取 Y 轴标签
 */
function extractYAxisLabel(option: any): string {
  if (!option.yAxis) return ''
  
  const yAxis = Array.isArray(option.yAxis) ? option.yAxis[0] : option.yAxis
  return yAxis?.name || ''
}

/**
 * 提取系列数据
 */
function extractSeriesData(option: any): Array<{
  name: string
  data: number[]
  type?: string
  unit?: string
  color?: string
}> {
  if (!option.series) return []
  
  return option.series.map((series: any) => ({
    name: series.name || '未知系列',
    data: series.data || [],
    type: series.type,
    unit: series.unit || '',
    color: series.itemStyle?.color || series.lineStyle?.color
  }))
}

/**
 * 将图表数据转换为自然语言描述
 * @param data 图表数据
 */
export function convertChartToText(data: ChartAnalysisRequest): string {
  let description = `这是一张${data.chartTitle}`
  
  switch (data.chartType) {
    case 'line':
      description += '折线图，展示了随时间变化的趋势。'
      break
    case 'bar':
      description += '柱状图，用于比较不同类别的数据。'
      break
    case 'pie':
      description += '饼图，显示了各部分占总体的比例。'
      break
    case 'area':
      description += '面积图，强调数量随时间的变化。'
      break
    case 'radar':
      description += '雷达图，用于多维度对比。'
      break
    case 'scatter':
      description += '散点图，展示数据点的分布。'
      break
    default:
      description += '图表。'
  }
  
  if (data.xAxis && data.xAxis.length > 0) {
    description += `\n时间范围：从${data.xAxis[0]}到${data.xAxis[data.xAxis.length - 1]}。`
  }
  
  if (data.series.length > 0) {
    description += `\n包含 ${data.series.length} 个数据系列：`
    data.series.forEach(s => {
      const numericData = s.data.filter(d => typeof d === 'number')
      if (numericData.length > 0) {
        const avg = numericData.reduce((a, b) => a + b, 0) / numericData.length
        const max = Math.max(...numericData)
        const min = Math.min(...numericData)
        description += `\n- ${s.name}：平均值${avg.toFixed(2)}，最大值${max}，最小值${min}`
      }
    })
  }
  
  return description
}
