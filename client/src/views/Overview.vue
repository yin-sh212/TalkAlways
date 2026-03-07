<template>
  <div class="overview-container">
    <!-- 顶部导航栏 -->
    <div class="header">
      <div class="logo">
        <h1>智慧能源管理系统</h1>
      </div>
      <div class="user-info">
        <n-space align="center" :size="12">
          <n-button size="small" @click="toggleTheme">
            <template #icon>
              <n-icon :component="isDark ? Sunny : Moon" />
            </template>
            {{ isDark ? '浅色' : '深色' }}
          </n-button>
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
              <div class="kpi-changes">
                <div class="kpi-change" :class="{ 'is-up': kpiData.dayChange >= 0 }">
                  <n-icon :component="kpiData.dayChange >= 0 ? ArrowUpward : ArrowDownward" />
                  {{ Math.abs(kpiData.dayChange).toFixed(1) }}%
                  <span class="change-label">较昨日</span>
                </div>
                <div class="kpi-change" :class="{ 'is-up': kpiData.weekChange >= 0 }">
                  <n-icon :component="kpiData.weekChange >= 0 ? ArrowUpward : ArrowDownward" />
                  {{ Math.abs(kpiData.weekChange).toFixed(1) }}%
                  <span class="change-label">较上周</span>
                </div>
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

      <!-- 新增：能耗排名 TOP5 -->
      <n-card title="能耗排名 TOP5" :bordered="false" content-style="padding: 20px;" class="ranking-card">
        <n-space vertical :size="16">
          <div v-for="(item, index) in rankingList" :key="item.buildingId" class="ranking-item">
            <div class="ranking-info">
              <n-tag :type="getRankingTagType(index)" size="small" class="ranking-tag">
                {{ index + 1 }}
              </n-tag>
              <span class="ranking-building">{{ item.buildingName }}</span>
              <n-progress
                :percentage="item.percentage"
                :color="getRankingColor(index)"
                :show-indicator="false"
                class="ranking-progress"
              />
              <span class="ranking-value">{{ item.energy.toFixed(2) }} MWh</span>
            </div>
          </div>
        </n-space>
      </n-card>

      <!-- 新增：设备状态监控面板 -->
      <n-grid :cols="2" :x-gap="16" :y-gap="16" class="device-grid">
        <n-grid-item>
          <n-card title="设备运行状态" :bordered="false" content-style="padding: 20px;">
            <template #header-extra>
              <n-tag :type="deviceStats.healthScore > 80 ? 'success' : 'warning'" size="small">
                健康度：{{ deviceStats.healthScore }}%
              </n-tag>
            </template>
            <n-skeleton v-if="loading" :rows="4" />
            <template v-else>
              <n-space vertical :size="16">
                <div class="device-stat-item">
                  <div class="stat-header">
                    <n-icon size="20" color="#52c41a"><CheckCircle /></n-icon>
                    <span class="stat-label">正常运行</span>
                  </div>
                  <div class="stat-value success">{{ deviceStats.normalCount }}</div>
                  <n-progress
                    :percentage="Math.round(deviceStats.normalCount / deviceStats.totalCount * 100)"
                    :color="'#52c41a'"
                    :show-indicator="false"
                  />
                </div>
                
                <div class="device-stat-item">
                  <div class="stat-header">
                    <n-icon size="20" color="#f5222d"><Alert /></n-icon>
                    <span class="stat-label">异常告警</span>
                  </div>
                  <div class="stat-value danger">{{ deviceStats.abnormalCount }}</div>
                  <n-progress
                    :percentage="Math.round(deviceStats.abnormalCount / deviceStats.totalCount * 100)"
                    :color="'#f5222d'"
                    :show-indicator="false"
                  />
                </div>
                
                <div class="device-stat-item">
                  <div class="stat-header">
                    <n-icon size="20" color="#faad14"><Warning /></n-icon>
                    <span class="stat-label">离线设备</span>
                  </div>
                  <div class="stat-value warning">{{ deviceStats.offlineCount }}</div>
                  <n-progress
                    :percentage="Math.round(deviceStats.offlineCount / deviceStats.totalCount * 100)"
                    :color="'#faad14'"
                    :show-indicator="false"
                  />
                </div>
                
                <div class="device-stat-item">
                  <div class="stat-header">
                    <n-icon size="20" color="#1890ff"><Layers /></n-icon>
                    <span class="stat-label">设备总数</span>
                  </div>
                  <div class="stat-value">{{ deviceStats.totalCount }}</div>
                </div>
              </n-space>
            </template>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="设备类型分布" :bordered="false" content-style="padding: 20px;">
            <n-skeleton v-if="loading" :rows="4" />
            <template v-else>
              <div ref="deviceChartRef" class="device-chart-container"></div>
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- 图表区 -->
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

      <!-- 异常列表区 -->
      <n-card title="实时异常/报警（最新 5 条）" :bordered="false" content-style="padding: 20px;">
        <template #header-extra>
          <n-space align="center">
            <span class="refresh-time">最后更新：{{ lastUpdateTime }}</span>
            <n-button text size="small" @click="toggleAutoRefresh">
              <template #icon>
                <n-icon :component="autoRefresh ? Stop : Play" />
              </template>
              {{ autoRefresh ? '停止刷新' : '自动刷新' }}
            </n-button>
            <n-button text size="small" @click="handleViewAll">
              查看全部
              <template #icon>
                <n-icon :component="ArrowRight" />
              </template>
            </n-button>
          </n-space>
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
  ChevronForwardOutline as ArrowRight,
  LinkOutline as LinkIcon,
  PlayOutline as Play,
  StopOutline as Stop,
  CheckmarkCircleOutline as CheckCircle,
  AlertOutline as Alert,
  WarningOutline as Warning,
  LayersOutline as Layers,
  SunnyOutline as Sunny,
  MoonOutline as Moon
} from '@vicons/ionicons5'
import { Flash as EnergyIcon, TvOutline as Device, LeafOutline as Leaf } from '@vicons/ionicons5'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const router = useRouter()
const dialog = useDialog()
const message = useMessage()
const userStore = useUserStore()

// 主题状态
const isDark = ref(false)

// 状态
const loading = ref(false)
const autoRefresh = ref(true) // 是否自动刷新
const refreshTimer = ref<any>(null)
const lastUpdateTime = ref('') // 最后更新时间
const kpiData = ref<KPIData>({
  totalEnergy: 0,
  energyChange: 0,
  dayChange: 0, // 日环比
  weekChange: 0, // 周同比
  deviceOnlineRate: 0,
  abnormalDeviceCount: 0,
  co2Reduction: 0
})
const chartData = ref({
  buildingEnergy: [] as any[],
  trendData: [] as any[]
})
const anomalyList = ref<AnomalyItem[]>([])
const rankingList = ref<any[]>([]) // 能耗排名数据
const deviceStats = ref({
  totalCount: 0,
  normalCount: 0,
  abnormalCount: 0,
  offlineCount: 0,
  healthScore: 0
}) // 设备统计数据
const pieChartRef = ref<HTMLElement | null>(null)
const lineChartRef = ref<HTMLElement | null>(null)
const deviceChartRef = ref<HTMLElement | null>(null) // 设备图表引用
let pieChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null
let deviceChart: echarts.ECharts | null = null // 设备图表实例

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

// 计算日环比（Mock 数据，实际应从后端获取）
const calculateDayChange = (currentEnergy: number) => {
  // TODO: 实际应从后端获取昨日数据
  const yesterdayEnergy = currentEnergy * (1 + Math.random() * 0.2 - 0.1)
  return ((currentEnergy - yesterdayEnergy) / yesterdayEnergy) * 100
}

// 计算周同比（Mock 数据，实际应从后端获取）
const calculateWeekChange = (currentEnergy: number) => {
  // TODO: 实际应从后端获取上周数据
  const lastWeekEnergy = currentEnergy * (1 + Math.random() * 0.3 - 0.15)
  return ((currentEnergy - lastWeekEnergy) / lastWeekEnergy) * 100
}

// 生成能耗排名数据
const generateRankingData = (buildingEnergy: any[]) => {
  if (!buildingEnergy || buildingEnergy.length === 0) {
    // Mock 数据
    rankingList.value = [
      { buildingId: '1', buildingName: '行政楼', energy: 350.5, percentage: 90 },
      { buildingId: '2', buildingName: '实验楼', energy: 280.3, percentage: 72 },
      { buildingId: '3', buildingName: '教学楼 A', energy: 220.8, percentage: 57 },
      { buildingId: '4', buildingName: '图书馆', energy: 180.2, percentage: 46 },
      { buildingId: '5', buildingName: '教学楼 B', energy: 150.6, percentage: 39 }
    ]
  } else {
    // 根据实际数据生成排名
    rankingList.value = buildingEnergy
      .map((item, index) => ({
        buildingId: String(index),
        buildingName: item.name,
        energy: item.value,
        percentage: 0 // 稍后计算
      }))
      .sort((a, b) => b.energy - a.energy)
      .slice(0, 5)
    
    // 计算百分比
    const maxEnergy = rankingList.value[0]?.energy || 1
    rankingList.value.forEach(item => {
      item.percentage = Math.round((item.energy / maxEnergy) * 100)
    })
  }
}

// 获取排名标签类型
const getRankingTagType = (index: number) => {
  if (index === 0) return 'error'
  if (index === 1) return 'warning'
  if (index === 2) return 'info'
  return 'default'
}

// 获取排名进度条颜色
const getRankingColor = (index: number) => {
  if (index === 0) return '#f5222d'
  if (index === 1) return '#faad14'
  if (index === 2) return '#1890ff'
  return '#52c41a'
}

// 更新最后更新时间
const updateLastUpdateTime = () => {
  const now = new Date()
  lastUpdateTime.value = now.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
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
      dayChange: calculateDayChange(summary.total_elec), // 日环比
      weekChange: calculateWeekChange(summary.total_elec), // 周同比
      deviceOnlineRate: 100, // 后端未提供，暂时设置为 100
      abnormalDeviceCount: anomalyRes.data.anomaly_count || 0, // 从异常数据中获取
      co2Reduction: (summary.total_elec || 0) * 0.785 // 根据能耗换算
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

    // 生成能耗排名数据
    generateRankingData(chartData.value.buildingEnergy)

    // 生成设备统计数据
    generateDeviceStats()

    // 初始化图表
    initCharts()
    
    // 更新最后更新时间
    updateLastUpdateTime()
  } catch (error: any) {
    console.error('加载数据失败:', error)
    message.error(error.message || '加载数据失败')
  } finally {
    loading.value = false
  }
}

// 生成设备统计数据（Mock 数据）
const generateDeviceStats = () => {
  // TODO: 实际应调用后端接口获取真实设备状态数据
  deviceStats.value = {
    totalCount: 150,
    normalCount: 128,
    abnormalCount: 12,
    offlineCount: 10,
    healthScore: Math.round((128 / 150) * 100)
  }
  
  // 初始化设备类型分布图
  setTimeout(() => {
    initDeviceChart()
  }, 100)
}

// 初始化设备类型分布图
const initDeviceChart = () => {
  if (!deviceChartRef.value) return
  
  deviceChart = echarts.init(deviceChartRef.value)
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}台 ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      data: ['空调机组', '照明系统', '电梯设备', '水泵设备', '其他']
    },
    series: [
      {
        name: '设备类型',
        type: 'pie',
        radius: '60%',
        data: [
          { value: 45, name: '空调机组', itemStyle: { color: '#1890ff' } },
          { value: 38, name: '照明系统', itemStyle: { color: '#52c41a' } },
          { value: 28, name: '电梯设备', itemStyle: { color: '#faad14' } },
          { value: 22, name: '水泵设备', itemStyle: { color: '#f5222d' } },
          { value: 17, name: '其他', itemStyle: { color: '#722ed1' } }
        ],
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
  
  deviceChart.setOption(option)
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
    
    // 添加点击事件监听，实现图表联动
    pieChart.on('click', (params: any) => {
      if (params.dataIndex !== undefined) {
        const buildingName = params.name
        message.info(`已选择：${buildingName}，图表将联动显示该建筑数据`)
        
        // 触发联动事件（这里可以调用其他图表的更新函数）
        // TODO: 实际应用中可以通过事件总线或状态管理来实现跨组件通信
        updateChartsWithBuilding(buildingName)
      }
    })
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

// 根据选中的建筑更新图表（联动功能）
const updateChartsWithBuilding = (buildingName: string) => {
  // TODO: 实际应用中应该调用后端接口获取该建筑的详细数据
  // 这里仅做演示，模拟更新折线图数据
  
  if (lineChart) {
    // 模拟数据减少为原来的 60%-80%
    const mockData = chartData.value.trendData.map(item => ({
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
  
  // 可以在这里添加更多联动逻辑，如更新异常列表等
}

// 刷新数据
const handleRefresh = () => {
  loadData()
  message.success('数据已刷新')
}

// 切换自动刷新
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startAutoRefresh()
    message.success('已开启自动刷新')
  } else {
    clearInterval(refreshTimer.value)
    message.info('已关闭自动刷新')
  }
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

// 切换主题
const toggleTheme = () => {
  isDark.value = !isDark.value
  
  // 应用深色类名到 html 元素
  if (isDark.value) {
    document.documentElement.classList.add('dark')
    message.success('已切换到深色模式')
  } else {
    document.documentElement.classList.remove('dark')
    message.success('已切换到浅色模式')
  }
  
  // TODO: 实际应用中应该保存到 localStorage 或用户配置
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

// 加载保存的主题
const loadSavedTheme = () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme === 'dark') {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
}

// 窗口大小变化时重新渲染图表
const handleResize = () => {
  pieChart?.resize()
  lineChart?.resize()
  deviceChart?.resize()
}

// 启动自动刷新
const startAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
  refreshTimer.value = setInterval(() => {
    if (autoRefresh.value) {
      loadData()
      message.success('数据已自动刷新')
    }
  }, 30000) // 30 秒刷新一次
}

onMounted(() => {
  loadSavedTheme() // 加载保存的主题
  loadData()
  startAutoRefresh() // 启动自动刷新
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
  pieChart?.dispose()
  lineChart?.dispose()
  deviceChart?.dispose()
})

</script>

<style scoped lang="scss">
// 深色主题变量
:root.dark {
  --bg-color: #1a1a1a;
  --card-bg: #242424;
  --text-primary: rgba(255, 255, 255, 0.9);
  --text-secondary: rgba(255, 255, 255, 0.65);
  --border-color: #424242;
}

.overview-container {
  width: 100%;
  height: 100%;
  background: var(--bg-color, #f0f2f5);
  display: flex;
  flex-direction: column;
  transition: background 0.3s ease;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--card-bg, white);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: background 0.3s ease;
  
  .refresh-time {
    font-size: 12px;
    color: var(--text-secondary, #999);
  }
  
  .logo {
    h1 {
      font-size: 24px;
      font-weight: bold;
      color: var(--text-primary, #1890ff);
      margin: 0;
      transition: color 0.3s ease;
    }
  }
  
  .user-info {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .username {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #333);
      transition: color 0.3s ease;
    }
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
    background: var(--card-bg, white);
    transition: background 0.3s ease;
    
    .card-title {
      font-size: 14px;
      color: var(--text-secondary, #666);
      font-weight: 500;
      transition: color 0.3s ease;
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

    .kpi-changes {
      display: flex;
      gap: 16px;
      margin-top: 8px;

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

// 新增：排名卡片样式
.ranking-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  
  .ranking-item {
    .ranking-info {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .ranking-tag {
        width: 24px;
        text-align: center;
      }
      
      .ranking-building {
        width: 100px;
        font-size: 14px;
        color: #333;
      }
      
      .ranking-progress {
        flex: 1;
      }
      
      .ranking-value {
        width: 100px;
        text-align: right;
        font-size: 14px;
        font-weight: 600;
        color: #1890ff;
      }
    }
  }
}

.device-grid {
  .device-stat-item {
    .stat-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      
      .stat-label {
        font-size: 14px;
        color: #666;
      }
    }
    
    .stat-value {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 8px;
      
      &.success {
        color: #52c41a;
      }
      
      &.danger {
        color: #f5222d;
      }
      
      &.warning {
        color: #faad14;
      }
    }
  }
  
  .device-chart-container {
    height: 250px;
    width: 100%;
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