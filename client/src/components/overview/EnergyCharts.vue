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
        <div v-else ref="distributionChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card title="近 7 日总能耗趋势" :bordered="false" content-style="padding: 20px;">
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="trendChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { LinkOutline as LinkIcon } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import { getSummary } from '@/api/statistics'

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
      lineStyle?: any
    }>
  }
}

const props = defineProps<Props>()

// 定义事件
const emit = defineEmits<{
  (e: 'buildingClick', buildingName: string): void
}>()

// 图表引用
const pieChartRef = ref<HTMLElement | null>(null)
const distributionChartRef = ref<HTMLElement | null>(null)
const trendChartRef = ref<HTMLElement | null>(null)

let pieChart: echarts.ECharts | null = null
let distributionChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

const message = useMessage()

// 初始化图表
const initCharts = () => {
  // 1. 环形图 - 各建筑能耗占比
  if (pieChartRef.value && props.buildingEnergy.length > 0) {
    // 如果已有图表实例，先销毁
    if (pieChart) {
      pieChart.dispose()
      pieChart = null
    }
    
    pieChart = echarts.init(pieChartRef.value)
    
    // 创建按建筑名称索引的映射
    const buildingMap = new Map(props.buildingEnergy.map(item => [item.name, item]))
    
    const pieOption: EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} MWh ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'middle'
      },
      series: [
        {
          name: '能耗占比',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: props.buildingEnergy.map(item => ({
            value: item.value,
            name: item.name
          })),
          // 添加点击事件
          selectedMode: 'single',
          selectedOffset: 10
        }
      ]
    }
    
    pieChart.setOption(pieOption)
    
    // 添加点击事件监听
    pieChart.on('click', async (params: any) => {
      if (params.data?.name) {
        emit('buildingClick', params.data.name)
      }
    })
  } else if (pieChartRef.value) {
    // 没有数据时显示空状态
    if (pieChart) {
      pieChart.dispose()
      pieChart = null
    }
    
    pieChart = echarts.init(pieChartRef.value)
    const emptyOption: EChartsOption = {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        }
      }
    }
    pieChart.setOption(emptyOption)
  }

  // 2. 折线图 - 24 小时能耗分布（使用 distribution 数据）
  if (distributionChartRef.value && props.distributionData) {
    // 如果已有图表实例，先销毁
    if (distributionChart) {
      distributionChart.dispose()
      distributionChart = null
    }
    
    distributionChart = echarts.init(distributionChartRef.value)
    const distData = props.distributionData
    
    const distOption: EChartsOption = {
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
        type: 'line' as const,
        smooth: true,
        data: s.data,
        areaStyle: s.areaStyle || { opacity: 0.3 },
        itemStyle: {
          color: '#18a058'
        },
        lineStyle: s.lineStyle
      }))
    }
    distributionChart.setOption(distOption)
  } else if (distributionChartRef.value) {
    // 没有数据时显示空状态
    if (distributionChart) {
      distributionChart.dispose()
      distributionChart = null
    }
    
    distributionChart = echarts.init(distributionChartRef.value)
    const emptyOption: EChartsOption = {
      tooltip: {
        trigger: 'axis'
      },
      xAxis: {
        type: 'category',
        data: []
      },
      yAxis: {
        type: 'value'
      },
      series: []
    }
    distributionChart.setOption(emptyOption)
  }

  // 3. 折线图 - 近 7 日总能耗趋势（使用 trend 数据）
  if (trendChartRef.value && props.trendData.length > 0) {
    // 如果已有图表实例，先销毁
    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }
    
    trendChart = echarts.init(trendChartRef.value)
    const trendOption: EChartsOption = {
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
    trendChart.setOption(trendOption)
  } else if (trendChartRef.value) {
    // 没有数据时显示空状态
    if (trendChart) {
      trendChart.dispose()
      trendChart = null
    }
    
    trendChart = echarts.init(trendChartRef.value)
    const emptyOption: EChartsOption = {
      tooltip: {
        trigger: 'axis'
      },
      xAxis: {
        type: 'category',
        data: []
      },
      yAxis: {
        type: 'value'
      },
      series: []
    }
    trendChart.setOption(emptyOption)
  }
}

// 根据选中的建筑更新图表（联动功能）
const updateChartsWithBuilding = async (buildingName: string) => {
  try {
    // 获取该建筑的7日趋势数据
    const today = new Date().toISOString().split('T')[0]
    const sevenDaysAgo = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    
    const response = await getSummary({
      building_id: buildingName,
      start_date: sevenDaysAgo,
      end_date: today,
      time_unit: 'day'
    })
    
    const summaryData = response.data.data.summary
    const totalEnergy = (summaryData.total_elec || 0) / 1000 // kWh to MWh
    
    // 更新折线图
    if (trendChart) {
      const newOption: EChartsOption = {
        title: {
          text: `${buildingName} - 近 7 日能耗趋势`,
          left: 'center'
        },
        series: [{
          data: props.trendData.map(item => item.energy * (totalEnergy / kpiData.value.totalEnergy))
        }]
      }
      
      trendChart?.setOption(newOption)
    }
    
    message.info(`已选择：${buildingName}，图表已联动`)
  } catch (error) {
    console.error('更新图表失败:', error)
    message.error('更新图表失败')
  }
}

// 暴露方法给父组件
defineExpose({
  updateChartsWithBuilding
})

// 窗口大小变化时重新渲染图表
const handleResize = () => {
  pieChart?.resize()
  distributionChart?.resize()
  trendChart?.resize()
}

// 监听数据变化重新渲染图表
watch(() => props.distributionData, () => {
  if (!props.loading) {
    initCharts()
  }
}, { deep: true })

watch(() => props.trendData, () => {
  if (!props.loading) {
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
  distributionChart?.dispose()
  trendChart?.dispose()
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