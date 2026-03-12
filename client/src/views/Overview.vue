<template>
  <div class="overview-container">
    <!-- 头部工具栏 -->
    <div class="header">
      <h2>能耗监控仪表盘</h2>
      <div class="toolbar">
        <span class="last-update">最后更新：{{ lastUpdateTime }}</span>
        <n-button 
          type="primary" 
          size="small"
          :loading="loading"
          @click="handleRefresh"
        >
          <template #icon>
            <n-icon :component="Refresh" />
          </template>
          刷新数据
        </n-button>
      </div>
    </div>

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
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '@/store/user'
import { Refresh } from '@vicons/ionicons5'
import { getKPIData, getChartData, getTrendData, getAnomalyList } from '@/api/dashboard'
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

    // 填充 KPI 数据 - getKPIData() 已经返回了处理好的数据
    kpiData.value = kpiRes
    
    // 填充图表数据 - distributionRes 已经是处理好的格式
    chartData.value = {
      buildingEnergy: [], // Distribution 数据不直接用于排名，先留空
      trendData: [],
      distributionData: distributionRes // 新增：保存分布图数据
    }
    
    // 从趋势图中提取数据（使用 trendRes）
    if (trendRes.data.data?.categories && trendRes.data.data?.series) {
      // 使用第一个 series 的数据作为趋势数据
      const firstSeries = trendRes.data.data.series[0]
      if (firstSeries) {
        chartData.value.trendData = trendRes.data.data.categories.map((date: string, index: number) => ({
          date: date,
          energy: firstSeries.data[index] || 0
        }))
      }
    }
    
    // 填充异常列表 - anomalyRes 是原始响应
    anomalyList.value = []
    if (anomalyRes.data.data?.anomalies && anomalyRes.data.data.anomalies.length > 0) {
      anomalyList.value = anomalyRes.data.data.anomalies.map((item: any) => ({
        id: item.timestamp || Date.now(),
        time: item.timestamp,
        buildingName: '建筑',
        type: '能耗异常',
        status: 'pending' as const,
        buildingId: anomalyRes.data.data.building_id || 'B001',
        timeRange: {
          start: anomalyRes.data.data.period.split(' 至 ')[0],
          end: anomalyRes.data.data.period.split(' 至 ')[1]
        }
      }))
    }

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

// 切换主题 - 现在只是切换按钮状态，实际跟随浏览器
const toggleTheme = () => {
  // 点击按钮时切换主题（用于测试或临时切换）
  const newIsDark = !isDark.value
  window.setTheme(newIsDark)
  
  if (newIsDark) {
    message.success('已切换到深色模式')
  } else {
    message.success('已切换到浅色模式')
  }
}

onMounted(() => {
  loadData()
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