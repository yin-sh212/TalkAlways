import http from './http'
import type { KPIData, ChartData, AnomalyItem, DashboardResponse } from '@/types/dashboard'

// Mock 数据 - 用于演示
const mockKPIData: DashboardResponse<KPIData> = {
  code: 200,
  message: 'success',
  data: {
    totalEnergy: 1256.8,
    energyChange: -3.5,
    deviceOnlineRate: 98,
    abnormalDeviceCount: 2,
    co2Reduction: 856.4
  }
}

const mockChartData: DashboardResponse<ChartData> = {
  code: 200,
  message: 'success',
  data: {
    buildingEnergy: [
      { name: '行政楼', value: 350.5, percentage: 28 },
      { name: '教学楼 A', value: 280.3, percentage: 22 },
      { name: '教学楼 B', value: 245.8, percentage: 20 },
      { name: '图书馆', value: 195.2, percentage: 15 },
      { name: '实验楼', value: 185.0, percentage: 15 }
    ],
    trendData: [
      { date: '2024-01-01', energy: 1156.5 },
      { date: '2024-01-02', energy: 1189.3 },
      { date: '2024-01-03', energy: 1210.8 },
      { date: '2024-01-04', energy: 1198.6 },
      { date: '2024-01-05', energy: 1245.2 },
      { date: '2024-01-06', energy: 1278.9 },
      { date: '2024-01-07', energy: 1256.8 }
    ]
  }
}

const mockAnomalyList: DashboardResponse<AnomalyItem[]> = {
  code: 200,
  message: 'success',
  data: [
    {
      id: '1',
      time: '2024-01-07 14:35:20',
      buildingName: '行政楼',
      type: '能耗突增',
      status: 'pending',
      buildingId: 'building-001',
      timeRange: {
        start: '2024-01-07T00:00:00',
        end: '2024-01-07T23:59:59'
      }
    },
    {
      id: '2',
      time: '2024-01-07 13:20:15',
      buildingName: '教学楼 A',
      type: '设备离线',
      status: 'processing',
      buildingId: 'building-002',
      timeRange: {
        start: '2024-01-07T00:00:00',
        end: '2024-01-07T23:59:59'
      }
    },
    {
      id: '3',
      time: '2024-01-07 11:45:30',
      buildingName: '图书馆',
      type: '能耗突降',
      status: 'resolved',
      buildingId: 'building-004',
      timeRange: {
        start: '2024-01-07T00:00:00',
        end: '2024-01-07T23:59:59'
      }
    },
    {
      id: '4',
      time: '2024-01-07 10:15:45',
      buildingName: '实验楼',
      type: '异常用电',
      status: 'pending',
      buildingId: 'building-005',
      timeRange: {
        start: '2024-01-07T00:00:00',
        end: '2024-01-07T23:59:59'
      }
    },
    {
      id: '5',
      time: '2024-01-07 09:30:10',
      buildingName: '教学楼 B',
      type: '设备离线',
      status: 'processing',
      buildingId: 'building-003',
      timeRange: {
        start: '2024-01-07T00:00:00',
        end: '2024-01-07T23:59:59'
      }
    }
  ]
}

// 获取 KPI 数据（使用 Mock）
export const getKPIData = () => {
  // return http.get<DashboardResponse<KPIData>>('/dashboard/kpi')
  return Promise.resolve(mockKPIData)
}

// 获取图表数据（使用 Mock）
export const getChartData = () => {
  // return http.get<DashboardResponse<ChartData>>('/dashboard/chart')
  return Promise.resolve(mockChartData)
}

// 获取异常列表（使用 Mock）
export const getAnomalyList = (limit = 5) => {
  // return http.get<DashboardResponse<AnomalyItem[]>>(`/dashboard/anomalies?limit=${limit}`)
  return Promise.resolve(mockAnomalyList)
}

// 跳转到分析页面并带入查询条件
export const navigateToAnalysis = (buildingId: string, timeRange: { start: string; end: string }) => {
  return `/analysis?building=${buildingId}&start=${timeRange.start}&end=${timeRange.end}`
}
