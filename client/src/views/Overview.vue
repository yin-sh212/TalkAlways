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
      <!-- KPI 卡片区 - 使用组件 -->
      <KpiCards :loading="loading" :kpiData="kpiData" />

      <!-- 能耗排名 TOP5 - 使用组件 -->
      <EnergyRanking :rankingList="rankingList" />

      <!-- 图表区 - 使用组件 -->
      <EnergyCharts 
        ref="energyChartsRef"
        :loading="loading" 
        :building-energy="chartData.buildingEnergy"
        :trend-data="chartData.trendData"
        @building-click="handleBuildingClick"
      />

      <!-- 设备监控 - 使用组件 -->
      <DeviceMonitor :loading="loading" :deviceStats="deviceStats" />

      <!-- 异常列表 - 使用组件 -->
      <AnomalyList 
        :loading="loading" 
        :anomaly-list="anomalyList"
        :last-update-time="lastUpdateTime"
        @view-all="handleViewAll"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '@/store/user'
import { Refresh } from '@vicons/ionicons5'
import { getKPIData, getChartData, getTrendData, getAnomalyList } from '@/api/dashboard'
import type { KPIData, ChartData, AnomalyItem } from '@/types/dashboard'
import EnergyCharts from '@/components/overview/EnergyCharts.vue'
import KpiCards from '@/components/overview/KpiCards.vue'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()

// 状态
const loading = ref(false)
const autoRefresh = ref(true)
const refreshTimer = ref<any>(null)
const lastUpdateTime = ref('')

const kpiData = ref<KPIData>({
  totalEnergy: 0,
  energyChange: 0,
  dayChange: 0,
  weekChange: 0,
  deviceOnlineRate: 0,
  abnormalDeviceCount: 0,
  co2Reduction: 0
})

const chartData = ref({
  buildingEnergy: [] as any[],
  trendData: [] as any[]
})

const anomalyList = ref<any[]>([])
const rankingList = ref<any[]>([])
const deviceStats = ref({
  totalCount: 0,
  normalCount: 0,
  abnormalCount: 0,
  offlineCount: 0,
  healthScore: 0
})

const energyChartsRef = ref<InstanceType<typeof EnergyCharts> | null>(null)

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

// 加载数据 - 并行调用三个接口
const loadData = async () => {
  loading.value = true
  try {
    // 并行调用：KPI 数据 + 分布图数据 + 趋势图数据 + 异常列表
    const [kpiRes, distributionRes, trendRes, anomalyRes] = await Promise.all([
      getKPIData(),
      getChartData(),
      getTrendData(),
      getAnomalyList(5)
    ])

    console.log('KPI 响应:', kpiRes)
    console.log('分布图响应:', distributionRes)
    console.log('趋势图响应:', trendRes)
    console.log('异常列表响应:', anomalyRes)

    // 填充 KPI 数据 - 注意：后端返回的数据在 data.data 中
    const summary = kpiRes.data.data?.summary || {}
    kpiData.value = {
      totalEnergy: summary.total_elec || 0,
      energyChange: 0,
      dayChange: calculateDayChange(summary.total_elec),
      weekChange: calculateWeekChange(summary.total_elec),
      deviceOnlineRate: 100,
      abnormalDeviceCount: anomalyRes.data.data?.anomaly_count || 0,
      co2Reduction: (summary.total_elec || 0) * 0.785
    }
    
    // 填充图表数据
    chartData.value = {
      buildingEnergy: distributionRes.data.data?.series || [],
      trendData: trendRes.data.data?.series?.[0]?.data.map((value: number, index: number) => ({
        date: trendRes.data.data.categories?.[index] || '',
        energy: value
      })) || []
    }
    
    // 填充异常列表 - 注意：后端返回的数据在 data.data 中
    anomalyList.value = anomalyRes.data.data?.anomalies?.map((item: any) => ({
      id: item.timestamp,
      time: item.timestamp,
      buildingName: '建筑',
      type: '能耗异常',
      status: 'pending' as const,
      buildingId: anomalyRes.data.data.building_id,
      timeRange: {
        start: anomalyRes.data.data.period.split(' 至 ')[0],
        end: anomalyRes.data.data.period.split(' 至 ')[1]
      }
    })) || []

    // 生成能耗排名数据
    generateRankingData(chartData.value.buildingEnergy)

    // 生成设备统计数据
    generateDeviceStats()
    
    // 更新最后更新时间
    updateLastUpdateTime()
  } catch (error: any) {
    console.error('加载数据失败:', error)
    message.error(error.message || '加载数据失败')
  } finally {
    loading.value = false
  }
}

// 处理建筑点击事件（图表联动）
const handleBuildingClick = (buildingName: string) => {
  if (energyChartsRef.value) {
    energyChartsRef.value.updateChartsWithBuilding(buildingName)
  }
}

// 刷新数据
const handleRefresh = () => {
  loadData()
  message.success('数据已刷新')
}

// 查看全部异常
const handleViewAll = () => {
  router.push('/analysis?showAllAnomalies=true')
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


onMounted(() => {
  loadData()
  startAutoRefresh() // 启动自动刷新
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})

</script>

<style scoped lang="scss">
// 深色主题变量
:root[data-theme="dark"] {
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
  
  .logo {
    h1 {
      font-size: 24px;
      font-weight: bold;
      color: var(--text-primary, #18a058);
      color: var(--text-primary, #18a058);
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
</style>