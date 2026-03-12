import http from './http'

// 获取趋势图数据
export const getTrendData = (params: { building_id?: string; days?: number }) => {
  return http.get('/charts/trend', { params })
}

// 获取对比图数据
export const getComparisonData = (params: { building_id?: string; start_date?: string; end_date?: string }) => {
  return http.get('/charts/comparison', { params })
}

// 获取分布图数据
export const getDistributionData = (params: { building_id?: string; date?: string }) => {
  return http.get('/charts/distribution', { params })
}