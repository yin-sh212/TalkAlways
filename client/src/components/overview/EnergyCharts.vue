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
import { ref, onMounted, onUnmounted, watch, nextTick, getCurrentInstance } from 'vue'
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

const message = useMessage()
const instance = getCurrentInstance()

// 重试配置
const MAX_RETRY_COUNT = 5
const RETRY_DELAY = 300

// 图表引用和实例管理
const pieChartRef = ref<HTMLElement | null>(null)
const distributionChartRef = ref<HTMLElement | null>(null)
const trendChartRef = ref<HTMLElement | null>(null)

// 使用 Map 统一管理所有图表实例，便于批量管理
const chartInstances = new Map<'pie' | 'distribution' | 'trend', echarts.ECharts | null>()
chartInstances.set('pie', null)
chartInstances.set('distribution', null)
chartInstances.set('trend', null)

// 重试计数器
const retryCounts = {
  pie: 0,
  distribution: 0,
  trend: 0
}

// 安全的图表初始化函数 - 带重试机制和尺寸检查
const safeInitChart = async (
  chartType: 'pie' | 'distribution' | 'trend',
  containerRef: typeof pieChartRef,
  initFn: () => void
): Promise<boolean> => {
  // 检查组件是否仍活跃
  if (!instance || !instance.isMounted) {
    console.warn(`[EnergyCharts] 组件未挂载，跳过 ${chartType} 初始化`)
    return false
  }

  const container = containerRef.value
  
  // 容器不存在时的兜底逻辑
  if (!container) {
    console.warn(`[EnergyCharts] ${chartType} 容器不存在，等待 DOM 创建`)
    retryCounts[chartType]++
    
    if (retryCounts[chartType] >= MAX_RETRY_COUNT) {
      console.error(`[EnergyCharts] ${chartType} 重试次数已达上限 (${MAX_RETRY_COUNT})，停止重试`)
      return false
    }
    
    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
    return safeInitChart(chartType, containerRef, initFn)
  }

  // 检查容器尺寸
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn(`[EnergyCharts] ${chartType} 容器尺寸为 0 (${container.offsetWidth}x${container.offsetHeight})`)
    retryCounts[chartType]++
    
    if (retryCounts[chartType] >= MAX_RETRY_COUNT) {
      console.error(`[EnergyCharts] ${chartType} 重试次数已达上限 (${MAX_RETRY_COUNT})，停止重试`)
      return false
    }
    
    // 等待下一帧并重试
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
    return safeInitChart(chartType, containerRef, initFn)
  }

  // 重置重试计数器
  retryCounts[chartType] = 0

  // 销毁旧实例（如果存在）
  const oldChart = chartInstances.get(chartType)
  if (oldChart && !oldChart.isDisposed()) {
    console.log(`[EnergyCharts] 销毁旧的 ${chartType} 图表实例`)
    oldChart.dispose()
    chartInstances.set(chartType, null)
  }

  try {
    // 初始化新实例
    initFn()
    console.log(`[EnergyCharts] ${chartType} 图表初始化成功`)
    return true
  } catch (error) {
    console.error(`[EnergyCharts] ${chartType} 初始化失败:`, error)
    return false
  }
}

// 统一的图表初始化入口
const initAllCharts = async () => {
  console.log('[EnergyCharts] 开始初始化所有图表')
  
  // 并行初始化所有图表，提高性能
  await Promise.all([
    // 1. 环形图 - 各建筑能耗占比
    safeInitChart('pie', pieChartRef, () => {
      const hasData = props.buildingEnergy && props.buildingEnergy.length > 0
      
      const chart = echarts.init(pieChartRef.value!)
      chartInstances.set('pie', chart)
      
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
            type: 'pie' as const,
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
            data: hasData 
              ? props.buildingEnergy.map(item => ({
                  value: item.value,
                  name: item.name
                }))
              : [],
            selectedMode: 'single',
            selectedOffset: 10
          }
        ]
      }
      
      chart.setOption(pieOption)
      
      // 添加点击事件监听
      chart.on('click', (params: any) => {
        if (params.data?.name) {
          emit('buildingClick', params.data.name)
        }
      })
    }),

    // 2. 折线图 - 24 小时能耗分布
    safeInitChart('distribution', distributionChartRef, () => {
      const chart = echarts.init(distributionChartRef.value!)
      chartInstances.set('distribution', chart)
      
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
          data: distData?.categories || []
        },
        yAxis: {
          type: 'value',
          name: '能耗 (kWh)',
          axisLabel: {
            formatter: '{value}'
          }
        },
        series: (distData?.series || []).map(s => ({
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
      
      chart.setOption(distOption)
    }),

    // 3. 折线图 - 近 7 日总能耗趋势
    safeInitChart('trend', trendChartRef, () => {
      const chart = echarts.init(trendChartRef.value!)
      chartInstances.set('trend', chart)
      
      const hasData = props.trendData && props.trendData.length > 0
      
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
          data: hasData ? props.trendData.map(item => item.date) : []
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
            type: 'line' as const,
            smooth: true,
            data: hasData ? props.trendData.map(item => item.energy) : [],
            areaStyle: {
              opacity: 0.3
            },
            itemStyle: {
              color: '#18a058'
            }
          }
        ]
      }
      
      chart.setOption(trendOption)
    })
  ])
}

// 响应式数据更新处理 - 直接更新 option 而不是重新初始化
const updateCharts = () => {
  console.log('[EnergyCharts] 更新图表数据')
  
  // 更新饼图数据
  const pieChart = chartInstances.get('pie')
  if (pieChart && !pieChart.isDisposed() && pieChartRef.value) {
    const hasData = props.buildingEnergy && props.buildingEnergy.length > 0
    pieChart.setOption({
      series: [{
        data: hasData 
          ? props.buildingEnergy.map(item => ({
              value: item.value,
              name: item.name
            }))
          : []
      }]
    })
  }

  // 更新分布图数据
  const distributionChart = chartInstances.get('distribution')
  if (distributionChart && !distributionChart.isDisposed() && distributionChartRef.value) {
    const distData = props.distributionData
    distributionChart.setOption({
      xAxis: {
        data: distData?.categories || []
      },
      series: (distData?.series || []).map(s => ({
        name: s.name,
        data: s.data
      }))
    })
  }

  // 更新趋势图数据
  const trendChart = chartInstances.get('trend')
  if (trendChart && !trendChart.isDisposed() && trendChartRef.value) {
    const hasData = props.trendData && props.trendData.length > 0
    trendChart.setOption({
      xAxis: {
        data: hasData ? props.trendData.map(item => item.date) : []
      },
      series: [{
        data: hasData ? props.trendData.map(item => item.energy) : []
      }]
    })
  }
}

// 根据选中的建筑更新图表（联动功能）
const updateChartsWithBuilding = async (buildingName: string) => {
  try {
    console.log('[EnergyCharts] 建筑点击联动:', buildingName)
    
    // 触发父组件的联动处理
    emit('buildingClick', buildingName)
    
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

// 窗口大小变化时重新渲染图表 - 使用 ResizeObserver 替代简单的 resize 监听
let resizeObserver: ResizeObserver | null = null

const setupResizeObserver = () => {
  // 清理旧的 observer
  if (resizeObserver) {
    resizeObserver.disconnect()
  }

  // 创建新的 observer
  resizeObserver = new ResizeObserver(() => {
    // 使用 requestAnimationFrame 优化性能
    requestAnimationFrame(() => {
      chartInstances.forEach((chart, type) => {
        if (chart && !chart.isDisposed()) {
          chart.resize()
        }
      })
    })
  })

  // 监听所有图表容器
  if (pieChartRef.value) resizeObserver.observe(pieChartRef.value)
  if (distributionChartRef.value) resizeObserver.observe(distributionChartRef.value)
  if (trendChartRef.value) resizeObserver.observe(trendChartRef.value)
}

// 监听数据变化 - 使用更精确的更新策略
watch(() => props.buildingEnergy, (newVal, oldVal) => {
  if (!props.loading) {
    console.log('[EnergyCharts] buildingEnergy 变化，尝试更新')
    // 如果图表已存在，直接更新数据；否则重新初始化
    if (chartInstances.get('pie') && !chartInstances.get('pie')?.isDisposed()) {
      updateCharts()
    } else {
      nextTick(() => initAllCharts())
    }
  }
}, { deep: true })

watch(() => props.distributionData, (newVal, oldVal) => {
  if (!props.loading) {
    console.log('[EnergyCharts] distributionData 变化，尝试更新')
    if (chartInstances.get('distribution') && !chartInstances.get('distribution')?.isDisposed()) {
      updateCharts()
    } else {
      nextTick(() => initAllCharts())
    }
  }
}, { deep: true })

watch(() => props.trendData, (newVal, oldVal) => {
  if (!props.loading) {
    console.log('[EnergyCharts] trendData 变化，尝试更新')
    if (chartInstances.get('trend') && !chartInstances.get('trend')?.isDisposed()) {
      updateCharts()
    } else {
      nextTick(() => initAllCharts())
    }
  }
}, { deep: true })

// 监听 loading 状态变化
watch(() => props.loading, (newLoading) => {
  if (!newLoading) {
    console.log('[EnergyCharts] loading 结束，初始化图表')
    nextTick(() => initAllCharts())
  }
})

onMounted(async () => {
  console.log('[EnergyCharts] 组件已挂载，loading:', props.loading)
  
  // 如果数据已就绪，立即初始化
  if (!props.loading) {
    await initAllCharts()
  }
  
  // 设置容器尺寸监听
  setupResizeObserver()
  
  // 保留 window resize 作为备用
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  console.log('[EnergyCharts] 组件即将卸载，清理资源')
  
  // 清理 ResizeObserver
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  
  // 清理 window resize 监听
  window.removeEventListener('resize', handleResize)
  
  // 统一清理所有图表实例
  chartInstances.forEach((chart, type) => {
    if (chart && !chart.isDisposed()) {
      console.log(`[EnergyCharts] 销毁 ${type} 图表实例`)
      chart.dispose()
      chartInstances.set(type, null)
    }
  })
  
  chartInstances.clear()
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