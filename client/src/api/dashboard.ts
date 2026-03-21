import http from './http'
import type { KPIData, ChartData, AnomalyItem, DashboardResponse, SummaryResponse, DistributionResponse, TrendResponse, AnomalyResponse } from '@/types/dashboard'
import { getSummary, detectAnomaly } from './statistics'
import { getDistributionData, getTrendData as getTrendDataFromCharts } from './charts'
import { getDeviceStatus } from './query'
import { useBuildingStore } from '@/store/building'

// 有效数据时间范围常量
export const VALID_DATE_START = '2016-07-01'
export const VALID_DATE_END = '2016-08-31'
// 使用有效范围内的一个固定日期作为"今天"
export const MOCK_TODAY = '2016-08-15'

// 获取当前建筑 ID
const getBuildingId = () => {
  const buildingStore = useBuildingStore()
  const buildingId = buildingStore.currentBuildingId || ''
  return buildingId
}

// 获取 KPI 数据 - 对接真实接口
export const getKPIData = async () => {
  // 后端接口：GET /api/statistics/summary?building_id=xxx&start_date=xxx&end_date=xxx&time_unit=day
  const buildingId = getBuildingId()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
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
  
  try {
    const response = await getSummary({
      building_id: buildingId,
      start_date: MOCK_TODAY,
      end_date: MOCK_TODAY,
      time_unit: 'day'
    })
    
    // 将后端数据转换为前端需要的格式
    const summaryData = response.data.data.summary
    
    // 如果没有数据，返回默认值
    if (!summaryData || summaryData.total_elec === null) {
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
export const getChartData = async () => {
  // 后端接口：GET /api/charts/distribution?building_id=xxx&date=xxx
  const buildingId = getBuildingId()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
    return {
      categories: [],
      series: []
    }
  }
  
  try {
    const response = await getDistributionData({
      building_id: buildingId,
      date: MOCK_TODAY
    })
    
    const distributionData = response.data.data
    
    // 直接返回后端返回的图表配置数据
    return {
      categories: distributionData.categories || [],
      series: distributionData.series || []
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
export const getTrendData = async () => {
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
    
    const trendResponse = response.data.data
    
    // 将后端返回的趋势数据转换为前端需要的格式
    // 后端返回：{ categories: ['2016-07-09', '2016-07-10', ...], series: [{name: '平均用电量', data: [...}] }
    if (trendResponse.categories && trendResponse.series && trendResponse.series.length > 0) {
      return trendResponse.categories.map((date: string, index: number) => ({
        date: date,
        energy: trendResponse.series[0].data[index] || 0
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
export const getAnomalyList = async (limit = 5) => {
  // 后端接口：GET /api/statistics/anomaly?building_id=xxx&start_date=xxx&end_date=xxx
  const buildingId = getBuildingId()
  
  if (!buildingId) {
    console.warn('未设置建筑 ID，返回默认数据')
    return {
      data: {
        code: 200,
        message: '成功',
        data: {
          building_id: '',
          period: `${MOCK_TODAY} 至 ${MOCK_TODAY}`,
          total_points: 0,
          anomaly_count: 0,
          anomalies: []
        }
      }
    }
  }
  
  try {
    const response = await detectAnomaly({
      building_id: buildingId,
      start_date: MOCK_TODAY,
      end_date: MOCK_TODAY,
      threshold: 2.0
    })
    
    return response
  } catch (error) {
    console.error('获取异常列表失败:', error)
    // 返回空响应
    return {
      data: {
        code: 200,
        message: '成功',
        data: {
          building_id: '',
          period: `${MOCK_TODAY} 至 ${MOCK_TODAY}`,
          total_points: 0,
          anomaly_count: 0,
          anomalies: []
        }
      }
    }
  }
}

// 跳转到分析页面并带入查询条件
export const navigateToAnalysis = (buildingId: string, timeRange: { start: string; end: string }) => {
  return `/analysis?building=${buildingId}&start=${timeRange.start}&end=${timeRange.end}`
}