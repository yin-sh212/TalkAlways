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

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

interface AlarmDataItem {
  alarmType: string
  severity: string
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle'
    },
    series: [
      {
        name: '告警类型',
        type: 'pie',
        radius: '60%',
        data: [],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }
  
  chart.setOption(option)
}

// 更新图表数据
const updateChart = (data: AlarmDataItem[]) => {
  if (!chart || data.length === 0) return
  
  // 按告警类型分组
  const typeMap = new Map<string, number>()
  data.forEach(item => {
    if (!typeMap.has(item.alarmType)) {
      typeMap.set(item.alarmType, 0)
    }
    typeMap.set(item.alarmType, typeMap.get(item.alarmType)! + 1)
  })
  
  const pieData = Array.from(typeMap.entries()).map(([name, value]) => ({
    name,
    value
  }))
  
  chart?.setOption({
    series: [
      {
        data: pieData
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
