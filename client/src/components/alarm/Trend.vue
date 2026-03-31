<template>
  <n-card title="告警趋势" :bordered="false" content-style="padding: 16px;">
    <template #header-extra>
      <n-space>
        <ChartAIAnalysis 
          :chart-ref="chartRef"
          chart-title="告警趋势"
          chart-type="line"
        />
        <n-tag type="info" size="small">按时间统计</n-tag>
      </n-space>
    </template>
    <div ref="chartRef" class="chart-container" style="height: 320px;"></div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { getLineChartConfig, CHART_COLORS } from '@/utils/echarts-config'
import ChartAIAnalysis from '@/components/common/ChartAIAnalysis.vue'

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

// 定义 props
const props = defineProps<{
  trendData?: any
  loading?: boolean
}>()

interface AlarmDataItem {
  time: string
  severity: string
  status: string
}

// 根据系列名称获取默认颜色
const getColorByName = (name: string): string => {
  const colorMap: Record<string, string> = {
    '紧急': '#f5222d',
    '重要': '#fa8c16',
    '一般': '#1890ff',
    '提示': '#52c41a',
    '平均用电量': '#1890ff',
    '最大用电量': '#fa8c16',
    '用电量 (kWh)': '#1890ff',
    '告警数量': '#1890ff'
  }
  return colorMap[name] || CHART_COLORS.primary
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  // 使用空数据初始化
  const option = getLineChartConfig([], [], {
    yAxisName: '告警数量'
  })
  
  chart.setOption(option)
}

// 更新图表数据
const updateChart = (data: any) => {
  if (!chart) return
  
  // 后端返回的是 { categories: [], series: [] } 格式
  if (!data || !data.categories || !data.series || data.categories.length === 0) {
    // 空数据或格式不对，清空图表
    chart?.setOption({
      xAxis: { data: [] },
      series: []
    })
    return
  }
  
  const categories = data.categories
  const series = data.series || []
  
  // 映射系列配置
  const seriesData = series.map((s: any) => ({
    name: s.name,
    data: s.data || [],
    areaStyle: !!s.areaStyle,
    smooth: s.smooth !== undefined ? s.smooth : true,
    color: s.color || getColorByName(s.name)
  }))
  
  const option = getLineChartConfig(categories, seriesData, {
    yAxisName: '告警数量',
    tooltipFormatter: '{b}: {c}'
  })
  
  chart.setOption(option)
}

// 监听 trendData 变化
watch(() => props.trendData, (newData) => {
  if (newData) {
    updateChart(newData)
  }
}, { deep: true })

// 处理 resize
const handleResize = () => {
  if (chart && !chart.isDisposed()) {
    chart.resize()
  }
}

// 清空图表
const clearChart = () => {
  chart?.clear()
}

onMounted(() => {
  initChart()
  
  // 添加 ResizeObserver 监听容器大小变化
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(chartRef.value)
  }
})

onUnmounted(() => {
  // 清理 ResizeObserver
  if (resizeObserver && chartRef.value) {
    resizeObserver.unobserve(chartRef.value)
    resizeObserver.disconnect()
  }
  
  chart?.dispose()
})

defineExpose({
  updateChart,
  clearChart
})
</script>