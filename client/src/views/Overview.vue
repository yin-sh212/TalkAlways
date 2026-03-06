<template>
  <div class="overview-container">
    <!-- 顶部导航栏 -->
    <div class="header">
      <div class="logo">
        <h1>智慧能源管理系统</h1>
      </div>
      <div class="user-info">
        <n-space align="center" :size="12">
          <n-button size="small" @click="handleRefresh" :loading="loading">
            <template #icon>
              <n-icon :component="Refresh" />
            </template>
            刷新
          </n-button>
          <n-avatar round size="medium">
            {{ userStore.userInfo?.username?.charAt(0).toUpperCase() }}
          </n-avatar>
          <span class="username">{{ userStore.userInfo?.username }}</span>
          <n-button text @click="handleLogout">退出登录</n-button>
        </n-space>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content">
      <!-- KPI 卡片区 -->
      <n-grid :cols="3" :x-gap="16" :y-gap="16" class="kpi-grid">
        <n-grid-item>
          <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
            <template #header>
              <n-space justify="space-between" align="center">
                <span class="card-title">今日总能耗</span>
                <n-icon size="24" color="#18a058">
                  <EnergyIcon />
                </n-icon>
              </n-space>
            </template>
            <n-skeleton v-if="loading" :rows="2" />
            <template v-else>
              <div class="kpi-value">
                {{ kpiData.totalEnergy.toFixed(2) }}
                <span class="unit">MWh</span>
              </div>
              <div class="kpi-change" :class="{ 'is-up': kpiData.energyChange >= 0 }">
                <n-icon :component="kpiData.energyChange >= 0 ? ArrowUpward : ArrowDownward" />
                {{ Math.abs(kpiData.energyChange).toFixed(1) }}%
                <span class="change-label">较昨日</span>
              </div>
            </template>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
            <template #header>
              <n-space justify="space-between" align="center">
                <span class="card-title">在线设备率</span>
                <n-icon size="24" color="#1890ff">
                  <Device />
                </n-icon>
              </n-space>
            </template>
            <n-skeleton v-if="loading" :rows="2" />
            <template v-else>
              <div class="kpi-value">
                {{ kpiData.deviceOnlineRate }}
                <span class="unit">%</span>
              </div>
              <div class="kpi-subtitle">
                <n-tag :type="kpiData.abnormalDeviceCount > 0 ? 'warning' : 'success'" size="small">
                  异常设备：{{ kpiData.abnormalDeviceCount }}
                </n-tag>
              </div>
            </template>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
            <template #header>
              <n-space justify="space-between" align="center">
                <span class="card-title">今日 CO₂减排</span>
                <n-icon size="24" color="#52c41a">
                  <Leaf />
                </n-icon>
              </n-space>
            </template>
            <n-skeleton v-if="loading" :rows="2" />
            <template v-else>
              <div class="kpi-value">
                {{ kpiData.co2Reduction.toFixed(1) }}
                <span class="unit">kg</span>
              </div>
              <div class="kpi-subtitle">
                <span class="sub-text">根据能耗换算</span>
              </div>
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- 图表区 -->
      <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-grid">
        <n-grid-item>
          <n-card title="各建筑能耗占比" :bordered="false" content-style="padding: 20px;">
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

      <!-- 异常列表区 -->
      <n-card title="实时异常/报警（最新 5 条）" :bordered="false" content-style="padding: 20px;">
        <template #header-extra>
          <n-button text size="small" @click="handleViewAll">
            查看全部
            <template #icon>
              <n-icon :component="ArrowRight" />
            </template>
          </n-button>
        </template>
        
        <n-skeleton v-if="loading" :rows="5" />
        <n-empty v-else-if="anomalyList.length === 0" description="暂无异常报警" />
        <n-data-table
          v-else
          :columns="tableColumns"
          :data="anomalyList"
          :row-key="(row: AnomalyItem) => row.id"
          striped
          @update:checked-row-keys="handleCheckAnomaly"
        />
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useDialog, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useUserStore } from '@/store/user'
import * as dashboardApi from '@/api/dashboard'
import type { AnomalyItem, KPIData, ChartData } from '@/types/dashboard'
import { NTag, NButton } from 'naive-ui'
import { 
  Refresh, 
  ArrowUpOutline as ArrowUpward, 
  ArrowDownOutline as ArrowDownward, 
  ChevronForwardOutline as ArrowRight 
} from '@vicons/ionicons5'
import { Flash as EnergyIcon, TvOutline as Device, LeafOutline as Leaf } from '@vicons/ionicons5'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const router = useRouter()
const dialog = useDialog()
const message = useMessage()
const userStore = useUserStore()

// 状态
const loading = ref(false)
const kpiData = ref<KPIData>({
  totalEnergy: 0,
  energyChange: 0,
  deviceOnlineRate: 0,
  abnormalDeviceCount: 0,
  co2Reduction: 0
})
const chartData = ref({
  buildingEnergy: [] as any[],
  trendData: [] as any[]
})
const anomalyList = ref<AnomalyItem[]>([])
const pieChartRef = ref<HTMLElement | null>(null)
const lineChartRef = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

// 表格列定义
const tableColumns: DataTableColumns = [
  {
    type: 'selection' as const
  },
  {
    title: '异常时间',
    key: 'time',
    width: 180
  },
  {
    title: '建筑名称',
    key: 'buildingName',
    width: 150
  },
  {
    title: '异常类型',
    key: 'type',
    width: 150,
    render: (row: any) => {
      return h(
        NTag,
        { type: getTypeTagType(row.type) },
        { default: () => row.type }
      )
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row: any) => {
      const statusMap: Record<string, any> = {
        pending: { type: 'warning', text: '待处理' },
        processing: { type: 'info', text: '处理中' },
        resolved: { type: 'success', text: '已解决' }
      }
      const status = statusMap[row.status] || { type: 'default', text: row.status }
      return h(
        NTag,
        { type: status.type, size: 'small' },
        { default: () => status.text }
      )
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right',
    render: (row: any) => {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => handleViewDetail(row as AnomalyItem)
        },
        { default: () => '查看详情' }
      )
    }
  }
]

// 获取异常类型对应的标签颜色
const getTypeTagType = (type: string) => {
  if (type.includes('突增')) return 'error'
  if (type.includes('突降')) return 'warning'
  if (type.includes('离线')) return 'info'
  return 'default'
}

// 加载数据 - 并行调用三个接口
const loadData = async () => {
  loading.value = true
  try {
    // 并行调用：KPI 数据 + 分布图数据 + 趋势图数据 + 异常列表
    const [kpiRes, distributionRes, trendRes, anomalyRes] = await Promise.all([
      dashboardApi.getKPIData(),
      dashboardApi.getChartData(),
      dashboardApi.getTrendData(),
      dashboardApi.getAnomalyList(5)
    ])

    console.log('KPI 响应:', kpiRes)
    console.log('分布图响应:', distributionRes)
    console.log('趋势图响应:', trendRes)
    console.log('异常列表响应:', anomalyRes)

    // 填充 KPI 数据（后端返回的是 summary 格式）
    // 需要从 kpiRes.data.summary 中提取数据
    const summary = kpiRes.data.summary || {}
    kpiData.value = {
      totalEnergy: summary.total_elec || 0,
      energyChange: 0, // 后端未提供，需要计算或设置为 0
      deviceOnlineRate: 100, // 后端未提供，暂时设置为 100
      abnormalDeviceCount: 0, // 需要从异常数据中获取
      co2Reduction: 0 // 后端未提供，暂时设置为 0
    }
    
    // 填充图表数据
    chartData.value = {
      buildingEnergy: distributionRes.data.data?.series || [],
      trendData: trendRes.data.data?.series?.[0]?.data.map((value: number, index: number) => ({
        date: trendRes.data.data.categories?.[index] || '',
        energy: value
      })) || []
    }
    
    // 填充异常列表
    anomalyList.value = anomalyRes.data.anomalies?.map((item: any) => ({
      id: item.timestamp,
      time: item.timestamp,
      buildingName: '建筑', // 后端未提供建筑名称
      type: '能耗异常',
      status: 'pending' as const,
      buildingId: anomalyRes.data.building_id,
      timeRange: {
        start: anomalyRes.data.period.split(' 至 ')[0],
        end: anomalyRes.data.period.split(' 至 ')[1]
      }
    })) || []

    // 初始化图表
    initCharts()
  } catch (error: any) {
    console.error('加载数据失败:', error)
    message.error(error.message || '加载数据失败')
  } finally {
    loading.value = false
  }
}

// 初始化图表
const initCharts = () => {
  // 环形图 - 各建筑能耗占比
  if (pieChartRef.value && chartData.value.buildingEnergy.length > 0) {
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
          data: chartData.value.buildingEnergy
        }
      ]
    }
    pieChart.setOption(pieOption)
  }

  // 折线图 - 近 7 日总能耗趋势
  if (lineChartRef.value && chartData.value.trendData.length > 0) {
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
        data: chartData.value.trendData.map(item => item.date)
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
          data: chartData.value.trendData.map(item => item.energy),
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

// 刷新数据
const handleRefresh = () => {
  loadData()
  message.success('数据已刷新')
}

// 查看异常详情
const handleViewDetail = (row: AnomalyItem) => {
  const url = dashboardApi.navigateToAnalysis(row.buildingId, row.timeRange)
  router.push(url)
}

// 查看全部异常
const handleViewAll = () => {
  router.push('/analysis?showAllAnomalies=true')
}

// 选中异常
const handleCheckAnomaly = (checkedRowKeys: (string | number)[]) => {
  console.log('选中的异常:', checkedRowKeys)
}

// 退出登录
const handleLogout = () => {
  dialog.warning({
    title: '退出登录',
    content: '确定要退出登录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      await userStore.logoutAction()
      message.success('已退出登录')
      router.push('/login')
    }
  })
}

// 窗口大小变化时重新渲染图表
const handleResize = () => {
  pieChart?.resize()
  lineChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  pieChart?.dispose()
  lineChart?.dispose()
})
</script>

<style scoped lang="scss">
.overview-container {
  width: 100%;
  height: 100%;
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.logo {
  h1 {
    font-size: 24px;
    font-weight: bold;
    color: #1890ff;
    margin: 0;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;

  .username {
    font-size: 14px;
    font-weight: 500;
    color: #333;
  }
}

.content {
  flex: 1;
  padding: 24px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.kpi-grid {
  .kpi-card {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    
    .card-title {
      font-size: 14px;
      color: #666;
      font-weight: 500;
    }

    .kpi-value {
      font-size: 32px;
      font-weight: bold;
      color: #333;
      margin: 16px 0;

      .unit {
        font-size: 14px;
        color: #999;
        margin-left: 4px;
      }
    }

    .kpi-change {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 14px;
      
      &.is-up {
        color: #f5222d;
      }
      
      &:not(.is-up) {
        color: #52c41a;
      }

      .change-label {
        font-size: 12px;
        color: #999;
        margin-left: 4px;
      }
    }

    .kpi-subtitle {
      margin-top: 8px;

      .sub-text {
        font-size: 12px;
        color: #999;
      }
    }
  }
}

.chart-grid {
  .chart-container {
    height: 300px;
    width: 100%;
  }
}

:deep(.n-card) {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
}

:deep(.n-data-table) {
  font-size: 14px;
}
</style>
