<template>
  <div class="overview-container">
    <!-- 主内容区 -->
    <div class="content">
      <!-- KPI 卡片区 -->
      <KpiCards :loading="loading" :kpiData="kpiData" />

      <!-- 能耗排名 TOP5 -->
      <EnergyRanking :rankingList="rankingList" />

      <!-- 图表区 -->
      <EnergyCharts 
        ref="energyChartsRef"
        :loading="loading" 
        :building-energy="chartData.buildingEnergy"
        :trend-data="chartData.trendData"
        :distribution-data="chartData.distributionData"
        @building-click="handleBuildingClick"
      />

      <!-- 设备监控 -->
      <DeviceMonitor :loading="loading" :deviceStats="deviceStats" />

      <!-- 异常列表 -->
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
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '@/store/user'
import { useBuildingStore } from '@/store/building'
import { getKPIData, getChartData, getAnomalyList, getTrendData, MOCK_TODAY } from '@/api/dashboard'
import { getSummary, detectAnomaly, getBuildingsSummary, getDailyComparison } from '@/api/statistics'
import { getBuildings, getDeviceStatus } from '@/api/query'
import type { KPIData, ChartData, AnomalyItem } from '@/types/dashboard'
import EnergyCharts from '@/components/overview/EnergyCharts.vue'
import KpiCards from '@/components/overview/KpiCards.vue'

// 声明全局 Window 类型
declare global {
  interface Window {
    setTheme: (dark: boolean) => void
    isDark: { value: boolean }
  }
}

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()
const buildingStore = useBuildingStore()

// 当前建筑 ID - 从 buildingStore 获取
const currentBuildingId = computed(() => {
  const id = buildingStore.currentBuildingId
  return id
})

// 主题状态 - 从全局获取（跟随浏览器）
const isDark = ref(window.isDark?.value || false)

// 监听全局主题变化
watch(() => window.isDark?.value, (newVal) => {
  isDark.value = newVal
})

// 状态
const loading = ref(false)
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
  trendData: [] as any[],
  distributionData: undefined as any
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

// 有效数据时间范围常量（已从 dashboard.ts 导入）
// MOCK_TODAY 已在 dashboard.ts 中定义并导入

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

// 更新设备统计数据
const updateDeviceStats = async () => {
  try {
    const response = await getDeviceStatus(currentBuildingId.value)
    const data = response.data.data
    
    deviceStats.value = {
      totalCount: data.totalCount || 0,
      normalCount: data.normalCount || 0,
      abnormalCount: data.abnormalCount || 0,
      offlineCount: data.offlineCount || 0,
      healthScore: Math.round(((data.normalCount || 0) / (data.totalCount || 1)) * 100)
    }
  } catch (error) {
    console.error('获取设备状态失败:', error)
    // 使用默认值
    deviceStats.value = {
      totalCount: 150,
      normalCount: 128,
      abnormalCount: 12,
      offlineCount: 10,
      healthScore: 85
    }
  }
}

// 更新今日 CO₂减排
const updateCO2Reduction = async () => {
  try {
    // 获取今日总能耗（使用有效数据范围内的日期）
    const summaryResponse = await getSummary({
      building_id: currentBuildingId.value,
      start_date: MOCK_TODAY,
      end_date: MOCK_TODAY,
      time_unit: 'day'
    })
    
    const totalEnergy = (summaryResponse.data.data.summary.total_elec || 0) / 1000 // kWh to MWh
    
    // 更新 KPI 数据中的 CO₂减排量
    kpiData.value.co2Reduction = Number((totalEnergy * 0.5).toFixed(1)) // 每 MWh 减排 0.5 吨 CO₂
  } catch (error) {
    console.error('更新 CO₂减排失败:', error)
  }
}

// 更新异常设备数量
const updateAbnormalDeviceCount = async () => {
  try {
    const anomalyResponse = await detectAnomaly({
      building_id: currentBuildingId.value,
      start_date: MOCK_TODAY,
      end_date: MOCK_TODAY,
      threshold: 2.0
    })
    
    // 更新 KPI 数据中的异常设备数量
    kpiData.value.abnormalDeviceCount = anomalyResponse.data.data.anomaly_count || 0
  } catch (error) {
    console.error('更新异常设备数量失败:', error)
  }
}

// 更新日环比和周同比 - 使用批量接口
const updateDayAndWeekChange = async () => {
  try {
    // 基于 MOCK_TODAY 动态计算昨日和上周同期
    const mockDate = new Date(MOCK_TODAY)
    const yesterday = new Date(mockDate)
    yesterday.setDate(yesterday.getDate() - 1)
    const lastWeek = new Date(mockDate)
    lastWeek.setDate(lastWeek.getDate() - 7)
    
    // 格式化为 YYYY-MM-DD
    const formatDate = (date: Date) => {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }
    
    const dates = [MOCK_TODAY, formatDate(yesterday), formatDate(lastWeek)]
    const response = await getDailyComparison({
      building_id: currentBuildingId.value,
      dates: dates
    })
    
    const dailyData = response.data.data.daily_data || []
    
    // 按日期映射数据
    const dataMap = new Map()
    dailyData.forEach((item: any) => {
      dataMap.set(item.date, item.total_elec || 0)
    })
    
    // 获取各日期的数据（如果没有数据则为 0）
    const todayEnergy = (dataMap.get(MOCK_TODAY) || 0) / 1000
    const yesterdayEnergy = (dataMap.get(formatDate(yesterday)) || 0) / 1000
    const lastWeekEnergy = (dataMap.get(formatDate(lastWeek)) || 0) / 1000
    
    // 更新日环比和周同比
    kpiData.value.dayChange = yesterdayEnergy > 0 ? ((todayEnergy - yesterdayEnergy) / yesterdayEnergy) * 100 : 0
    kpiData.value.weekChange = lastWeekEnergy > 0 ? ((todayEnergy - lastWeekEnergy) / lastWeekEnergy) * 100 : 0
  } catch (error) {
    console.error('更新日环比和周同比失败:', error)
  }
}

// 更新建筑能耗占比数据 - 使用批量接口
const updateBuildingEnergyData = async () => {
  try {
    // 获取建筑列表
    const buildingsResponse = await getBuildings()
    const buildings = buildingsResponse.data.data || []
    
    // 提取所有建筑 ID
    const buildingIds = buildings.map((building: any) => 
      typeof building === 'string' ? building : (building.id || building.building_id)
    )
    
    // 批量获取所有建筑的能耗数据
    const response = await getBuildingsSummary({
      start_date: MOCK_TODAY,
      end_date: MOCK_TODAY,
      time_unit: 'day',
      building_ids: buildingIds
    })
    
    const buildingsData = response.data.data.buildings || []
    
    // 按建筑 ID 汇总
    const buildingEnergyMap = new Map()
    buildingsData.forEach((item: any) => {
      const buildingId = item.building_id
      const energy = (item.total_elec || 0) / 1000
      const current = buildingEnergyMap.get(buildingId) || { name: item.building_name || `建筑${buildingId}`, value: 0 }
      current.value += energy
      buildingEnergyMap.set(buildingId, current)
    })
    
    // 转换为数组并排序
    const buildingEnergyResults = Array.from(buildingEnergyMap.values())
    
    // 过滤掉值为 0 的建筑，并按能量值排序
    const filteredBuildingEnergy = buildingEnergyResults
      .filter(item => item.value > 0)
      .sort((a, b) => b.value - a.value)
    
    // 更新图表数据
    chartData.value.buildingEnergy = filteredBuildingEnergy
    
    // 生成能耗排名数据
    generateRankingData(filteredBuildingEnergy)
  } catch (error) {
    console.error('更新建筑能耗数据失败:', error)
    // 使用 mock 数据
    generateRankingData([])
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

// 获取当前建筑 ID
const fetchCurrentBuildingId = async () => {
  try {
    // 如果 buildingStore 中已有建筑 ID，直接使用
    if (buildingStore.currentBuildingId) {
      return
    }
    
    // 否则从接口获取建筑列表
    await buildingStore.fetchBuildings()
    
    if (!buildingStore.currentBuildingId && buildingStore.buildings.length > 0) {
      // 使用第一个建筑的 ID（已经是字符串）
      const firstBuildingId = buildingStore.buildings[0].id
      buildingStore.setCurrentBuildingId(firstBuildingId)
    } else if (!buildingStore.currentBuildingId) {
      // 如果没有建筑列表，使用默认值
      buildingStore.setCurrentBuildingId('B001')
    }
  } catch (error) {
    console.error('获取建筑 ID 失败:', error)
    // 使用默认值
    buildingStore.setCurrentBuildingId('B001')
  }
}

// 加载数据 - 并行调用多个接口
const loadData = async () => {
  // 确保建筑 ID 已获取后再加载数据
  if (!currentBuildingId.value) {
    await fetchCurrentBuildingId()
  }
  
  loading.value = true
  try {
    // 并行调用：KPI 数据 + 分布图数据（24 小时）+ 趋势数据（近 7 日）+ 异常列表
    const [kpiRes, distributionRes, trendRes, anomalyRes] = await Promise.all([
      getKPIData(),
      getChartData(),
      getTrendData(),
      getAnomalyList(5)
    ])

    // 填充 KPI 数据
    kpiData.value = kpiRes
    
    // 填充图表数据 - 分别使用不同的数据源
    chartData.value = {
      ...chartData.value,
      distributionData: distributionRes, // 24 小时能耗分布
      trendData: trendRes                // 近 7 日总能耗趋势（独立数据）
    }
    
    // 填充异常列表
    anomalyList.value = []
    if (anomalyRes.data.data?.anomalies && anomalyRes.data.data.anomalies.length > 0) {
      anomalyList.value = anomalyRes.data.data.anomalies.map((item: any) => ({
        id: item.timestamp || Date.now(),
        time: item.timestamp,
        buildingName: '建筑',
        type: '能耗异常',
        status: 'pending' as const,
        buildingId: currentBuildingId.value,
        timeRange: {
          start: anomalyRes.data.data.period.split(' 至 ')[0],
          end: anomalyRes.data.data.period.split(' 至 ')[1]
        }
      })).slice(0, 5) // 只取前 5 条
    }
    
    // 等待建筑能耗数据和设备统计数据更新完成
    await updateBuildingEnergyData()
    await updateDeviceStats()
    
    // 并行调用其他更新函数
    await Promise.all([
      updateCO2Reduction(),
      updateAbnormalDeviceCount(),
      updateDayAndWeekChange()
    ])
    
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
  loading.value = true
  loadData().finally(() => {
    loading.value = false
  })
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
  // 先获取建筑 ID，再加载数据
  fetchCurrentBuildingId().then(loadData)
})

onUnmounted(() => {
  // 清理逻辑已移除，不再需要清除定时器
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
  background: var(--bg-color);
  display: flex;
  flex-direction: column;
  transition: background 0.3s ease;
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