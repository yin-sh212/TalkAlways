<template>
  <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-grid">
    <n-grid-item>
      <n-card title="各建筑能耗占比" :bordered="false" content-style="padding: 20px;">
        <template #header-extra>
          <n-tooltip>
            <template #trigger>
              <n-icon size="18" style="cursor: pointer; color: #18a058;" :component="LinkIcon" />
            </template>
            点击环形图的某个建筑，其他图表将联动显示该建筑数据
          </n-tooltip>
        </template>
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="pieChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card title="24 小时能耗分布" :bordered="false" content-style="padding: 20px;">
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="lineChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card title="近 7 日总能耗趋势" :bordered="false" content-style="padding: 20px;">
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="lineChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, withDefaults } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { LinkOutline as LinkIcon } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'

interface TrendDataItem {
  date: string
  energy: number
}

interface Props {
  loading: boolean
  buildingEnergy: any[]
  trendData: TrendDataItem[]
  distributionData?: {
    categories: string[]
    series: Array<{
      name: string
      type: string
      data: number[]
      areaStyle?: any
    }>
  }
}

const props = withDefaults(defineProps<Props>(), {
  distributionData: undefined
})

// 定义事件
const emit = defineEmits<{
  (e: 'buildingClick', buildingName: string): void
}>()

const pieChartRef = ref<HTMLElement | null>(null)
const lineChartRef = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

const message = useMessage()

// 初始化图表
const initCharts = () => {
  // 折线图 - 24 小时能耗分布（使用 distribution 数据）
  if (lineChartRef.value && props.distributionData) {
    lineChart = echarts.init(lineChartRef.value)
    const distData = props.distributionData
    
    const lineOption: EChartsOption = {
      tooltip: {
        trigger: 'axis',
        formatter: '{b}: {c} kWh'
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
        data: distData.categories
      },
      yAxis: {
        type: 'value',
        name: '能耗 (kWh)',
        axisLabel: {
          formatter: '{value}'
        }
      },
      series: distData.series.map(s => ({
        name: s.name,
        type: s.type,
        smooth: true,
        data: s.data,
        areaStyle: s.areaStyle || { opacity: 0.3 },
        itemStyle: {
          color: '#18a058'
        }
      }))
    }
    lineChart.setOption(lineOption)
  } else if (lineChartRef.value && props.trendData.length > 0) {
    // 如果没有 distribution 数据，使用 trendData 作为后备
    lineChart = echarts.init(lineChartRef.value)
    const lineOption: EChartsOption = {
      tooltip: {
        trigger: 'axis',
        formatter: '{b}: {c} MWh'
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
        data: props.trendData.map(item => item.date)
      },
      yAxis: {
        type: 'value',
        name: '能耗 (MWh)',
        axisLabel: {
          formatter: '{value}'
        }
      },
      series: [
        {
          name: '总能耗',
          type: 'line',
          smooth: true,
          data: props.trendData.map(item => item.energy),
          areaStyle: {
            opacity: 0.3
          },
          itemStyle: {
            color: '#18a058'
          }
        }
      ]
    }
    lineChart.setOption(lineOption)
  }
  
  // 环形图暂时隐藏，等后端提供建筑排名数据后再启用
  // if (pieChartRef.value && props.buildingEnergy.length > 0) { ... }
}

// 根据选中的建筑更新图表（联动功能）
const updateChartsWithBuilding = (buildingName: string) => {
  if (lineChart) {
    // 模拟数据减少为原来的 60%-80%
    const mockData = props.trendData.map(item => ({
      date: item.date,
      energy: item.energy * (0.6 + Math.random() * 0.2)
    }))
    
    const newOption: EChartsOption = {
      title: {
        text: `${buildingName} - 近 7 日能耗趋势`,
        left: 'center'
      },
      series: [{
        data: mockData.map(item => item.energy)
      }]
    }
    
    lineChart?.setOption(newOption)
  }
}

// 暴露方法给父组件
defineExpose({
  updateChartsWithBuilding
})

// 窗口大小变化时重新渲染图表
const handleResize = () => {
  pieChart?.resize()
  lineChart?.resize()
}

// 监听数据变化重新渲染图表
watch(() => props.distributionData, () => {
  if (!props.loading) {
    initCharts()
  }
}, { deep: true })

watch(() => props.trendData, () => {
  if (!props.loading && !props.distributionData) {
    initCharts()
  }
}, { deep: true })

watch(() => props.buildingEnergy, () => {
  if (!props.loading) {
    initCharts()
  }
}, { deep: true })

onMounted(() => {
  if (!props.loading) {
    initCharts()
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  lineChart?.dispose()
})
</script>

<style scoped lang="scss">
.chart-grid {
  .chart-container {
    height: 300px;
    width: 100%;
  }
}
</style>
