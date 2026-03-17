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
let resizeObserver: ResizeObserver | null = null

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
const updateChart = (data: any) => {
  if (!chart) return
  
  // 情况 1：后端返回 { categories: [], series: [] } - 时间序列数据（折线图）
  if (data.categories && data.series) {
    const categories = data.categories
    const series = data.series || []
    
    chart?.setOption({
      xAxis: {
        type: 'category',
        data: categories,
        boundaryGap: false
      },
      yAxis: {
        type: 'value',
        name: '告警数量'
      },
      tooltip: {
        trigger: 'axis'
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
      series: series.map((s: any) => ({
        name: s.name,
        type: s.type || 'line',
        data: s.data || [],
        smooth: s.smooth !== undefined ? s.smooth : true,
        areaStyle: s.areaStyle ? { opacity: 0.3 } : undefined,
        itemStyle: { color: s.color || '#1890ff' },
        lineStyle: s.lineStyle || {}
      }))
    })
    return
  }
  
  // 情况 2：后端返回数组 - 分类统计数据（饼图）
  if (Array.isArray(data) && data.length > 0) {
    const pieData = data.map(item => ({
      name: item.name || item.type || item.category || item.alarm_type,
      value: item.value || item.count || 0
    }))
    
    chart?.setOption({
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
          name: '告警分布',
          type: 'pie',
          radius: '60%',
          data: pieData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    })
    return
  }
  
  // 空数据或格式不对，清空图表
  chart?.setOption({
    xAxis: { data: [] },
    series: []
  })
}

// 清空图表
const clearChart = () => {
  chart?.clear()
}

// 处理 resize
const handleResize = () => {
  if (chart && !chart.isDisposed()) {
    chart.resize()
  }
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

<style scoped>
.chart-container {
  width: 100%;
}
</style>
