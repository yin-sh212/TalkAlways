import http from './http'
import type { KPIData, ChartData, AnomalyItem, DashboardResponse, SummaryResponse, DistributionResponse } from '@/types/dashboard'

// 获取 KPI 数据 - 对接真实接口
export const getKPIData = async () => {
  // 后端接口：GET /api/statistics/summary?building_id=xxx&start_date=xxx&end_date=xxx&time_unit=day
  const today = new Date().toISOString().split('T')[0]
  
  try {
    const response = await http.get<DashboardResponse<SummaryResponse>>('/statistics/summary', {
      params: {
        building_id: 'B001',  // 默认建筑
        start_date: today,
        end_date: today,
        time_unit: 'day'  // 修正：参数名应为 time_unit 而不是 group_by
      }
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
        co2Reduction: 0
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
      co2Reduction: Number((totalEnergy * 0.5).toFixed(1)) // 估算：每 MWh 减排 0.5 吨 CO₂
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
      co2Reduction: 0
    }
  }
}

// 获取图表数据 - 对接真实接口
export const getChartData = async () => {
  // 后端接口：GET /api/charts/distribution?building_id=xxx&date=xxx
  const today = new Date().toISOString().split('T')[0]
  
  try {
    const response = await http.get<DashboardResponse<DistributionResponse>>('/charts/distribution', {
      params: {
        building_id: 'B001',
        date: today
      }
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

// 获取趋势数据 - 对接真实接口
export const getTrendData = () => {
  // 后端接口：GET /api/charts/trend?building_id=xxx&days=7
  return http.get('/charts/trend', {
    params: {
      building_id: 'B001',
      days: 7
    }
  })
}

// 获取异常列表 - 对接真实接口
export const getAnomalyList = (limit = 5) => {
  // 后端接口：GET /api/statistics/anomaly?building_id=xxx&start_date=xxx&end_date=xxx
  const today = new Date().toISOString().split('T')[0]
  
  return http.get('/statistics/anomaly', {
    params: {
      building_id: 'B001',
      start_date: today,
      end_date: today,
      threshold: 2.0
    }
  })
}

// 跳转到分析页面并带入查询条件
export const navigateToAnalysis = (buildingId: string, timeRange: { start: string; end: string }) => {
  return `/analysis?building=${buildingId}&start=${timeRange.start}&end=${timeRange.end}`
}
