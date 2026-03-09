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
const updateChart = (data: AlarmDataItem[]) => {
  if (!chart || data.length === 0) return
  
  // 按时间和级别分组
  const timeMap = new Map<string, any>()
  data.forEach(item => {
    if (!timeMap.has(item.time)) {
      timeMap.set(item.time, {
        critical: 0,
        major: 0,
        minor: 0,
        warning: 0
      })
    }
    const timeData = timeMap.get(item.time)
    timeData[item.severity]++
  })
  
  const times = Array.from(timeMap.keys()).sort()
  const criticalData = times.map(t => timeMap.get(t).critical)
  const majorData = times.map(t => timeMap.get(t).major)
  const minorData = times.map(t => timeMap.get(t).minor)
  const warningData = times.map(t => timeMap.get(t).warning)
  
  chart?.setOption({
    xAxis: {
      data: times
    },
    series: [
      {
        name: '紧急',
        type: 'line',
        smooth: true,
        data: criticalData,
        itemStyle: { color: '#f5222d' },
        areaStyle: { opacity: 0.1 }
      },
      {
        name: '重要',
        type: 'line',
        smooth: true,
        data: majorData,
        itemStyle: { color: '#fa8c16' },
        areaStyle: { opacity: 0.1 }
      },
      {
        name: '一般',
        type: 'line',
        smooth: true,
        data: minorData,
        itemStyle: { color: '#1890ff' },
        areaStyle: { opacity: 0.1 }
      },
      {
        name: '提示',
        type: 'line',
        smooth: true,
        data: warningData,
        itemStyle: { color: '#52c41a' },
        areaStyle: { opacity: 0.1 }
      }
    ]
  })
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
