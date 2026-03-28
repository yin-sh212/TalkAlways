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
      />

      <!-- 异常列表 -->
      <AnomalyList 
        :loading="loading" 
        :anomaly-list="anomalyList"
        :last-update-time="lastUpdateTime"
        :current-simulate-time="currentSimulateTime"
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
import { useAppStore } from '@/store/app'
import { getKPIData, getChartData, getTrendData } from '@/api/dashboard'
import { getAlarmList as fetchAlarmList } from '@/api/alarm'
import type { KPIData } from '@/types/dashboard'
import EnergyCharts from '@/components/overview/EnergyCharts.vue'
import KpiCards from '@/components/overview/KpiCards.vue'
import { getBuildingsSummary, getDailyComparison, calculateCOP } from '@/api/statistics'
import { getBuildings } from '@/api/query'

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
const appStore = useAppStore()

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

// 实时推送相关
const eventSource = ref<EventSource | null>(null)
const isRealtimeConnected = ref(false)
const realtimeStartTime = ref('2016-09-03 00:00:00') // 固定从 9 月 3 日 0 点开始
const currentSimulateTime = ref('2016-09-03 00:00:00') // 当前模拟时间，初始为开始时间

const kpiData = ref<KPIData>({
  totalEnergy: 0,
  energyChange: 0,
  dayChange: 0,
  weekChange: 0,
  deviceOnlineRate: 0,
  abnormalDeviceCount: 0,
  cop: 0 // COP(能效比)
})

const chartData = ref({
  buildingEnergy: [] as any[],
  trendData: [] as any[],
  distributionData: undefined as any
})

const anomalyList = ref<any[]>([])
const rankingList = ref<any[]>([])

const energyChartsRef = ref<InstanceType<typeof EnergyCharts> | null>(null)

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

// 更新 COP(能效比)
const updateCOP = async () => {
  try {
    const appStore = useAppStore()
    const mockToday = appStore.getMockToday()
    const lastWeek = appStore.getLastWeek()
    
    // 调用 COP 计算接口
    const response = await calculateCOP({
      building_id: currentBuildingId.value,
      start_date: lastWeek,
      end_date: mockToday
    })
    
    // 后端返回格式：{ avg_cop_cooling, avg_cop_heating, cop_type, evaluation, details }
    const copData = response.data?.data
    
    // 使用 avg_cop_cooling 属性，如果没有则使用默认值
    const cop = copData?.avg_cop_cooling || 3.5
    kpiData.value.cop = Number(cop.toFixed(2))
  } catch (error) {
    console.error('更新 COP 失败:', error)
    // 使用默认值
    kpiData.value.cop = 3.5 // 典型 COP 值
  }
}

// 更新日环比和周同比 - 使用批量接口
const updateDayAndWeekChange = async () => {
  try {
    const appStore = useAppStore()
    const mockToday = appStore.getMockToday()
    const yesterday = appStore.getYesterday()
    const lastWeek = appStore.getLastWeek()
    
    const dates = [mockToday, yesterday, lastWeek]
    const response = await getDailyComparison({
      building_id: currentBuildingId.value,
      dates: dates
    })
    
    const dailyData = response.data?.data?.daily_data || []
    
    // 按日期映射数据
    const dataMap = new Map()
    dailyData.forEach((item: any) => {
      dataMap.set(item.date, item.total_elec || 0)
    })
    
    const todayEnergy = (dataMap.get(mockToday) || 0) / 1000
    const yesterdayEnergy = (dataMap.get(yesterday) || 0) / 1000
    const lastWeekEnergy = (dataMap.get(lastWeek) || 0) / 1000
    
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
    const mockToday = appStore.getMockToday()
    
    // 获取建筑列表
    const buildingsResponse = await getBuildings()
    const buildings = buildingsResponse.data?.data || []
    
    // 提取所有建筑 ID
    const buildingIds = buildings.map((building: any) => 
      typeof building === 'string' ? building : (building.id || building.building_id)
    )
    
    // 批量获取所有建筑的能耗数据
    const response = await getBuildingsSummary({
      start_date: mockToday,
      end_date: mockToday,
      time_unit: 'day',
      building_ids: buildingIds
    })
    
    const buildingsData = response.data?.data?.buildings || []
    
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
    const [kpiRes, distributionRes, trendRes, alarmRes] = await Promise.all([
      getKPIData(),
      getChartData(),
      getTrendData(),
      fetchAlarmList({ status: 'pending', page_size: 5 })
    ])

    // 填充 KPI 数据 - 使用 Object.assign 保持响应式引用
    if (kpiRes) {
      Object.assign(kpiData.value, {
        totalEnergy: kpiRes.totalEnergy ?? 0,
        energyChange: kpiRes.energyChange ?? 0,
        dayChange: kpiRes.dayChange ?? 0,
        weekChange: kpiRes.weekChange ?? 0,
        deviceOnlineRate: kpiRes.deviceOnlineRate ?? 100,
        abnormalDeviceCount: kpiRes.abnormalDeviceCount ?? 0
        // cop 属性不覆盖，由后续 updateCOP() 单独更新
      })
    }
    
    // 填充图表数据 - 分别使用不同的数据源
    chartData.value = {
      ...chartData.value,
      distributionData: distributionRes, // 24 小时能耗分布
      trendData: trendRes                // 近 7 日总能耗趋势（独立数据）
    }
    
    // 填充异常列表 - 始终保留最近的 5 条未解决告警
    anomalyList.value = []
    
    const alarmData = alarmRes.data?.data
    if (alarmData?.items && Array.isArray(alarmData.items)) {
      const alarms = alarmData.items
      
      anomalyList.value = alarms.map((item: any) => ({
        id: item.id,
        time: item.start_time,
        buildingName: item.building_id,
        type: mapAlarmTypeToChinese(item.alarm_type),
        status: mapAlarmStatus(item.status),
        buildingId: item.building_id,
        meterId: item.meter_id || '',
        description: item.description || `告警 ${item.id}`,
        timeRange: {
          start: item.start_time,
          end: item.end_time || item.start_time
        }
      }))
    } else {
      console.log('⚠️ 无告警数据')
    }

    // 等待建筑能耗数据更新完成
    await updateBuildingEnergyData()
    
    // 并行调用其他更新函数
    await Promise.all([
      updateCOP(),
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

// 查看全部异常
const handleViewAll = () => {
  router.push('/alarm')
}

// 连接到实时数据流
const connectToRealtimeStream = () => {
  try {
    // 关闭之前的连接
    if (eventSource.value) {
      eventSource.value.close()
    }
    
    const params = new URLSearchParams({
      start_date: realtimeStartTime.value,
      end_date: '2016-09-30 23:59:59',
      speed: '1', // 真实速度
      batch_hours: '1' // 每次推送 1 小时的数据，每隔 1 小时推送一次
    })
    
    const url = `http://localhost:3000/api/realtime/stream?${params}`
    
    eventSource.value = new EventSource(url)
    isRealtimeConnected.value = true
    
    eventSource.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'start') {
        } 
        else if (data.type === 'data') {
          // 更新当前模拟时间
          if (data.batch_start) {
            currentSimulateTime.value = formatTimestamp(data.batch_start)
          }
          
          // 检查是否有异常数据
          if (data.records && data.records.length > 0) {
            const anomalies = data.records.filter((r: any) => r.is_anomaly)
            
            if (anomalies.length > 0) {
              // 将异常添加到列表
              anomalies.forEach((record: any) => {
                const anomalyItem = {
                  id: `${record.building_id}_${record.timestamp}`,
                  time: record.timestamp,
                  buildingName: record.building_id,
                  type: '能耗异常',
                  status: 'pending' as const,
                  buildingId: record.building_id,
                  meterId: record.meter_id,
                  electricity: record.electricity,
                  ambientTemp: record.ambient_temp,
                  // 显示算法检测的详细信息
                  description: record.anomaly_info 
                    ? `用电量 ${record.electricity.toFixed(2)} kWh (Z-score: ${record.anomaly_info.z_score?.toFixed(2) || 'N/A'})`
                    : `用电量 ${record.electricity.toFixed(2)} kWh`,
                  anomalyInfo: record.anomaly_info // 保存完整的异常信息
                }
                
                // 避免重复添加
                const exists = anomalyList.value.some(
                  item => item.id === anomalyItem.id
                )
                
                if (!exists) {
                  anomalyList.value.unshift(anomalyItem)
                  
                  // 移除已解决的告警，保持列表中始终是最近的 5 条未解决告警
                  const unresolvedIndex = anomalyList.value.findIndex(
                    item => item.status === 'resolved'
                  )
                  
                  if (unresolvedIndex !== -1 && anomalyList.value.length > 5) {
                    // 如果超过 5 条且有已解决的，移除最后一条已解决的
                    anomalyList.value.splice(unresolvedIndex, 1)
                  } else if (anomalyList.value.length > 5) {
                    // 如果没有已解决的，直接移除最后一条
                    anomalyList.value.pop()
                  }
                  
                  // 播放提示音或显示通知
                  message.warning(`发现异常：${record.building_id} - ${record.meter_id}`)
                }
              })
            }
          }
        } 
        else if (data.type === 'progress') {
        }
        else if (data.type === 'complete') {
          message.success('数据回放完成')
          disconnectRealtimeStream()
        }
        else if (data.type === 'error') {
          console.error('❌ 流错误:', data.message)
          message.error(`数据流错误：${data.message}`)
          disconnectRealtimeStream()
        }
      } catch (error) {
        console.error('解析 SSE 数据失败:', error)
      }
    }
    
    eventSource.value.onerror = () => {
      console.error('❌ SSE 连接错误')
      message.error('实时数据连接中断')
      disconnectRealtimeStream()
    }
    
  } catch (error) {
    console.error('连接实时数据流失败:', error)
    message.error('连接失败')
    isRealtimeConnected.value = false
  }
}

// 断开实时数据流
const disconnectRealtimeStream = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  isRealtimeConnected.value = false
}

// 格式化时间戳
const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (e) {
    return timestamp
  }
}

// 告警类型映射（英文 -> 中文）
const mapAlarmTypeToChinese = (type: string): string => {
  const typeMap: Record<string, string> = {
    'energy': '能耗异常',
    'dynamic_baseline': '动态基线异常',
    'trend_decline': '趋势下降异常',
    'threshold': '阈值告警',
    'device': '设备告警'
  }
  return typeMap[type] || type
}

// 告警状态映射
const mapAlarmStatus = (status: string): 'pending' | 'processing' | 'resolved' => {
  const statusMap: Record<string, 'pending' | 'processing' | 'resolved'> = {
    'pending': 'pending',
    'acknowledged': 'processing',
    'confirmed': 'processing',
    'resolved': 'resolved'
  }
  return statusMap[status] || 'pending'
}

onMounted(() => {
  // 先获取建筑 ID，再加载数据
  fetchCurrentBuildingId().then(loadData)
  
  const appStore = useAppStore()
  const mockDateTime = appStore.getMockDateTime()
  realtimeStartTime.value = mockDateTime
  currentSimulateTime.value = mockDateTime
  
  // 延迟 2 秒后启动实时数据流
  setTimeout(() => {
    connectToRealtimeStream()
  }, 2000)
})

onUnmounted(() => {
  // 清理逻辑已移除，不再需要清除定时器
  disconnectRealtimeStream()
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