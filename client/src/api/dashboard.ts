import http from './http'
import type { KPIData, ChartData, AnomalyItem, DashboardResponse } from '@/types/dashboard'

// 获取 KPI 数据 - 对接真实接口
export const getKPIData = () => {
  // 后端接口：GET /api/statistics/summary?building_id=xxx&start_date=xxx&end_date=xxx
  // 这里需要构造合适的参数
  const today = new Date().toISOString().split('T')[0]
  
  return http.get('/statistics/summary', {
    params: {
      building_id: 'B001',  // 默认建筑
      start_date: today,
      end_date: today,
      group_by: 'day'
    }
  })
}

// 获取图表数据 - 对接真实接口
export const getChartData = () => {
  // 后端接口：GET /api/charts/distribution?building_id=xxx&date=xxx
  const today = new Date().toISOString().split('T')[0]
  
  return http.get('/charts/distribution', {
    params: {
      building_id: 'B001',
      date: today
    }
  })
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
