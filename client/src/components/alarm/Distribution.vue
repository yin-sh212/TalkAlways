<template>
  <n-card title="告警分布" :bordered="false" content-style="padding: 16px;">
    <template #header-extra>
      <n-space>
        <ChartAIAnalysis 
          :chart-ref="chartRef"
          chart-title="告警分布"
          chart-type="pie"
        />
        <n-tag type="info" size="small">按类型统计</n-tag>
      </n-space>
    </template>
    <div ref="chartRef" class="chart-container" style="height: 320px;"></div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { getBasePieChartConfig, getLineChartConfig, CHART_COLORS } from '@/utils/echarts-config'
import ChartAIAnalysis from '@/components/common/ChartAIAnalysis.vue'

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

// 定义 props
const props = defineProps<{
  distributionData?: any
  loading?: boolean
}>()

interface AlarmDataItem {
  alarmType: string
  severity: string
}

// 监听 distributionData 变化
watch(() => props.distributionData, (newData) => {
  if (newData) {
    updateChart(newData)
  }
}, { deep: true })

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  // 使用默认空数据初始化
  const option = getBasePieChartConfig([], {
    showLegend: true
  })
  
  chart.setOption(option)
}

// 监听窗口大小变化
const handleResize = () => {
  chart?.resize()
}

// 生命周期钩子
onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})

// 更新图表数据
const updateChart = (data: any) => {
  if (!chart) return
  
  // 情况 1：后端返回数组 - 分类统计数据（饼图）
  if (Array.isArray(data) && data.length > 0) {
    const pieData = data.map(item => ({
      name: item.name || item.type || item.category || item.alarm_type,
      value: item.value || item.count || 0
    }))
    
    const option = getBasePieChartConfig(pieData, {
      showLegend: true
    })
    
    chart.setOption(option)
    return
  }
  
  // 情况 2：后端返回 { categories: [], series: [] } - 时间序列数据（折线图），不适用于告警分布
  if (data.categories && data.series) {
    // 对于告警分布，直接使用 series[0].data 中的 name 和 value
    const pieData = (data.series[0]?.data || []).map((item: any) => ({
      name: item.name,
      value: item.value
    }))
    
    const option = getBasePieChartConfig(pieData, {
      showLegend: true
    })
    
    chart.setOption(option)
    return
  }
  
  // 空数据情况
  chart.setOption({
    series: [{
      data: []
    }]
  })
}

// 清空图表
const clearChart = () => {
  chart?.clear()
}

defineExpose({
  updateChart,
  clearChart
})
</script>