<template>
  <n-card title="告警分布" :bordered="false" content-style="padding: 16px;">
    <template #header-extra>
      <n-space>
        <n-tag type="info" size="small">按类型统计</n-tag>
      </n-space>
    </template>
    <div ref="chartRef" class="chart-container" style="height: 320px;"></div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { getBasePieChartConfig, getLineChartConfig, CHART_COLORS } from '@/utils/echarts-config'

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

interface AlarmDataItem {
  alarmType: string
  severity: string
}

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

// 更新图表数据
const updateChart = (data: any) => {
  if (!chart) return
  
  // 情况 1：后端返回 { categories: [], series: [] } - 时间序列数据（折线图）
  if (data.categories && data.series) {
    const categories = data.categories
    const series = data.series || []
    
    const seriesData = series.map((s: any) => ({
      name: s.name,
      data: s.data || [],
      areaStyle: !!s.areaStyle,
      smooth: s.smooth !== undefined ? s.smooth : true,
      color: s.color || CHART_COLORS.primary
    }))
    
    const option = getLineChartConfig(categories, seriesData, {
      yAxisName: '告警数量',
      tooltipFormatter: '{b}: {c}'
    })
    
    chart.setOption(option)
    return
  }
  
  // 情况 2：后端返回数组 - 分类统计数据（饼图）TODO?
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