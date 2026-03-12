import http from './http'

// 获取时段汇总
export const getSummary = (params: { building_id?: string; start_date?: string; end_date?: string; time_unit?: string }) => {
  return http.get('/statistics/summary', { params })
}

// 计算能效比 (COP)
export const calculateCOP = (params: { building_id?: string; start_date?: string; end_date?: string }) => {
  return http.get('/statistics/cop', { params })
}

// 检测能耗异常
export const detectAnomaly = (params: { building_id?: string; start_date?: string; end_date?: string; threshold?: number }) => {
  return http.get('/statistics/anomaly', { params })
}