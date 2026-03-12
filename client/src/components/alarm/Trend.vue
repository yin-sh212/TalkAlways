<template>
  <n-card title="告警趋势" :bordered="false" content-style="padding: 16px;">
    <template #header-extra>
      <n-space>
        <n-tag type="info" size="small">按时间统计</n-tag>
      </n-space>
    </template>
    <div ref="chartRef" class="chart-container" style="height: 320px;"></div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

interface AlarmDataItem {
  time: string
  severity: string
  status: string
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['紧急', '重要', '一般', '提示']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: []
    },
    yAxis: {
      type: 'value',
      name: '告警数量'
    },
    series: []
  }
  
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
  const mappedSeries = series.map((s: any) => ({
    name: s.name,
    type: (s.type || 'line') as 'line' | 'bar',
    smooth: s.smooth !== undefined ? s.smooth : true,
    data: s.data || [],
    itemStyle: { 
      color: s.color || getColorByName(s.name) 
    },
    areaStyle: s.areaStyle ? { opacity: 0.1 } : undefined,
    lineStyle: s.lineStyle || {}
  }))
  
  chart?.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: series.map((s: any) => s.name)
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: categories
    },
    yAxis: {
      type: 'value',
      name: '告警数量'
    },
    series: mappedSeries
  })
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
  return colorMap[name] || '#1890ff'
}

// 清空图表
const clearChart = () => {
  chart?.clear()
}

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  chart?.dispose()
})

defineExpose({
  updateChart,
  clearChart
})
</script>

<style scoped>
.chart-container {
  width: 100%;
}
</style>
