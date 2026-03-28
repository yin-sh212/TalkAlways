import type { KPIData, ChartData, DashboardResponse, AnomalyItem } from '@/types/dashboard'
import { getSummary as getStatisticsSummary, detectAnomaly as detectStatisticsAnomaly } from './statistics'
import { getEnergyDistributionData, getTrendData as getTrendDataFromCharts } from './charts'
import { useBuildingStore } from '@/store/building'
import { useAppStore } from '@/store/app'
import type { StatisticsSummaryResponse } from '@/types/statistics'

// 有效数据时间范围常量
export const VALID_DATE_START = '2016-07-01'
export const VALID_DATE_END = '2016-08-31'

// 获取当前建筑 ID
const getBuildingId = () => {
  const buildingStore = useBuildingStore()
  const buildingId = buildingStore.currentBuildingId || ''
  return buildingId
}

// 获取 Mock 日期
const getMockToday = () => {
  const appStore = useAppStore()
  return appStore.MOCK_TODAY
}

// 获取 KPI 数据 - 对接真实接口
export const getKPIData = async (): Promise<KPIData> => {
  // 后端接口：GET /api/statistics/summary?building_id=xxx&start_date=xxx&end_date=xxx&time_unit=day
  const buildingId = getBuildingId()
  const mockToday = getMockToday()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
    return {
      totalEnergy: 0,
      energyChange: 0,
      dayChange: 0,
      weekChange: 0,
      deviceOnlineRate: 100,
      abnormalDeviceCount: 0,
      cop: 0
    }
  }
  
  try {
    const response = await getStatisticsSummary({
      building_id: buildingId,
      start_date: mockToday,
      end_date: mockToday,
      time_unit: 'day'
    })
    
    // 将后端数据转换为前端需要的格式
    const apiData = response.data?.data as StatisticsSummaryResponse | undefined
    
    // 后端返回结构：{ building_id, summary: { total_elec, ... }, details: [] }
    const summaryData = apiData?.summary
    
    // 如果没有数据，返回默认值
    if (!summaryData || summaryData.total_elec === null || summaryData.total_elec === undefined) {
      console.warn('[getKPIData] 没有数据，返回默认值')
      return {
        totalEnergy: 0,
        energyChange: 0,
        dayChange: 0,
        weekChange: 0,
        deviceOnlineRate: 100,
        abnormalDeviceCount: 0,
        // co2Reduction: 0,
        cop: 0
      }
    }
    
    // 计算总能耗（从 kWh 转换为 MWh）
    const totalEnergy = (summaryData.total_elec || 0) / 1000
    
    return {
      totalEnergy: Number(totalEnergy.toFixed(2)),
      energyChange: 0, // 需要额外接口计算
      dayChange: 0,    // 需要昨天数据对比
      weekChange: 0,   // 需要上周数据对比
      deviceOnlineRate: 100, // 需要设备状态接口
      abnormalDeviceCount: 0, // 需要异常检测接口
      cop: 0 // COP 将在 Overview.vue 中通过 calculateCOP 接口单独获取
    }
  } catch (error) {
    console.error('获取 KPI 数据失败:', error)
    // 返回默认数据
    return {
      totalEnergy: 0,
      energyChange: 0,
      dayChange: 0,
      weekChange: 0,
      deviceOnlineRate: 100,
      abnormalDeviceCount: 0,
      // co2Reduction: 0,
      cop: 0
    }
  }
}

// 获取图表数据 - 对接真实接口
export const getChartData = async (): Promise<ChartData> => {
  // 后端接口：GET /api/charts/energy-distribution?building_id=xxx&date=xxx
  const buildingId = getBuildingId()
  const mockToday = getMockToday()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
    return {
      categories: [],
      series: []
    }
  }
  
  try {
    const response = await getEnergyDistributionData({
      building_id: buildingId,
      date: mockToday
    })
    
    const distributionData = response.data?.data
    
    // 直接返回后端返回的图表配置数据
    return {
      categories: distributionData?.categories || [],
      series: distributionData?.series || []
    }
  } catch (error) {
    console.error('获取图表数据失败:', error)
    // 返回空数据
    return {
      categories: [],
      series: []
    }
  }
}

// 获取趋势数据 - 对接真实接口（近 7 日总能耗趋势）
export const getTrendData = async (): Promise<Array<{ date: string; energy: number }>> => {
  // 后端接口：GET /api/charts/trend?building_id=xxx&days=7
  const buildingId = getBuildingId()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
    return []
  }
  
  try {
    const response = await getTrendDataFromCharts({
      building_id: buildingId,
      days: 7
    })
    
    const trendData = response.data?.data
    
    // 将后端返回的趋势数据转换为前端需要的格式
    if (trendData?.categories && trendData?.series && trendData.series.length > 0) {
      return trendData.categories.map((date: string, index: number) => ({
        date: date,
        energy: trendData.series[0].data[index] || 0
      }))
    }
    
    return []
  } catch (error) {
    console.error('获取趋势数据失败:', error)
    // 返回空数组
    return []
  }
}

// 获取异常列表 - 对接真实接口
export const getAnomalyList = async (limit = 5): Promise<DashboardResponse<AnomalyItem[]>> => {
  // 后端接口：GET /api/statistics/anomaly?building_id=xxx&start_date=xxx&end_date=xxx
  const buildingId = getBuildingId()
  const mockToday = getMockToday()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
    return {
      code: 200,
      message: '成功',
      data: []
    }
  }
  
  try {
    const response = await detectStatisticsAnomaly({
      building_id: buildingId,
      start_date: mockToday,
      end_date: mockToday,
      threshold: 2.0
    })
    
    const results = response.data?.data?.results
    let anomalies: any[] = []
    
    if (results) {
      // 如果是多指标（all），results 是对象；如果是单指标，results 可能就是对象
      if (results.electricity) {
        // 多指标情况
        anomalies = results.electricity.anomalies || []
      }
    }
    
    // 将响应转换为 DashboardResponse 格式
    return {
      code: response.data?.code || 200,
      message: response.data?.message || '成功',
      data: anomalies.map(anomaly => ({
        id: anomaly.timestamp,
        time: anomaly.timestamp,
        timeRange: {
          start: anomaly.timestamp,
          end: anomaly.timestamp
        },
        buildingName: buildingId,
        type: '能耗异常',
        status: 'pending' as const,
        buildingId: buildingId,
        meterId: '',
        electricity: anomaly.value,
        description: `用电量 ${anomaly.value?.toFixed(2) || '0'} kWh`
      }))
    }
  } catch (error) {
    console.error('获取异常列表失败:', error)
    return {
      code: 500,
      message: '获取失败',
      data: []
    }
  }
}

// 跳转到分析页面并带入查询条件
export const navigateToAnalysis = (buildingId: string, timeRange: { start: string; end: string }) => {
  return `/analysis?building=${buildingId}&start=${timeRange.start}&end=${timeRange.end}`
}