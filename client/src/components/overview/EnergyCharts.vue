<template>
  <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-grid">
    <n-grid-item>
      <n-card title="各建筑能耗占比" :bordered="false" content-style="padding: 20px;">
        <template #header-extra>
          <n-tooltip>
            <template #trigger>
              <n-icon size="18" style="cursor: pointer; color: #1890ff;" :component="LinkIcon" />
            </template>
            点击环形图的某个建筑，其他图表将联动显示该建筑数据
          </n-tooltip>
        </template>
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="pieChartRef" class="chart-container"></div>
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
import { ref, onMounted, onUnmounted, watch } from 'vue'
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
}

const props = defineProps<Props>()

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
  // 环形图 - 各建筑能耗占比
  if (pieChartRef.value && props.buildingEnergy.length > 0) {
    pieChart = echarts.init(pieChartRef.value)
    const pieOption: EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
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
              fontSize: 20,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: props.buildingEnergy
        }
      ]
    }
    pieChart.setOption(pieOption)
    
    // 添加点击事件监听，实现图表联动
    pieChart.on('click', (params: any) => {
      if (params.dataIndex !== undefined) {
        const buildingName = params.name
        message.info(`已选择：${buildingName}，图表将联动显示该建筑数据`)
        emit('buildingClick', buildingName)
      }
    })
  }

  // 折线图 - 近 7 日总能耗趋势
  if (lineChartRef.value && props.trendData.length > 0) {
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
            color: '#1890ff'
          }
        }
      ]
    }
    lineChart.setOption(lineOption)
  }
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
