import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 格式化日期为 YYYY-MM-DD
  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  // Mock 日期 - 基于真实当前时间计算
  // 计算逻辑：用真实当前时间减去 N 天，使日期回到 2016 年，但保持时分秒不变
  const calculateMockToday = (): string => {
    const now = new Date() // 真实当前时间，如 2026-03-28 15:05:40
    
    // 目标基准日期：2016-09-01（可以根据需要调整）
    const targetBaseDate = new Date('2016-09-01T00:00:00')
    
    // 计算当前时间与基准日期的天数差
    const oneDay = 24 * 60 * 60 * 1000 // 一天的毫秒数
    const daysDiff = Math.floor((now.getTime() - targetBaseDate.getTime()) / oneDay)
    
    // 用基准日期加上时分秒部分
    const mockDate = new Date('2016-09-01T00:00:00')
    mockDate.setHours(now.getHours(), now.getMinutes(), now.getSeconds(), now.getMilliseconds())
    
    return formatDate(mockDate)
  }
  
  const MOCK_TODAY = ref<string>(calculateMockToday())
  
  // 设置 Mock 日期
  const setMockToday = (date: string) => {
    MOCK_TODAY.value = date
  }
  
  // 获取 Mock 日期
  const getMockToday = () => {
    return MOCK_TODAY.value
  }
  
  // 计算昨日日期
  const getYesterday = (): string => {
    const mockDate = new Date(MOCK_TODAY.value)
    mockDate.setDate(mockDate.getDate() - 1)
    return formatDate(mockDate)
  }
  
  // 计算上周同期（7 天前）
  const getLastWeek = (): string => {
    const mockDate = new Date(MOCK_TODAY.value)
    mockDate.setDate(mockDate.getDate() - 7)
    return formatDate(mockDate)
  }
  
  // 计算本月（往前推 30 天）
  const getLastMonth = (): string => {
    const mockDate = new Date(MOCK_TODAY.value)
    mockDate.setDate(mockDate.getDate() - 29)
    return formatDate(mockDate)
  }
  
  // 获取今日时间范围（00:00:00 至 23:59:59）
  const getTodayRange = (): { start: string; end: string } => {
    const mockDate = new Date(MOCK_TODAY.value)
    const start = new Date(mockDate.setHours(0, 0, 0, 0))
    const end = new Date(mockDate.setHours(23, 59, 59, 999))
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0]
    }
  }
  
  // 获取本周时间范围（周一至周日）
  const getWeekRange = (): { start: string; end: string } => {
    const mockDate = new Date(MOCK_TODAY.value)
    const dayOfWeek = mockDate.getDay() || 7 // 将周日转换为 7
    const monday = new Date(mockDate)
    monday.setDate(mockDate.getDate() - (dayOfWeek - 1))
    monday.setHours(0, 0, 0, 0)
    
    const sunday = new Date(monday)
    sunday.setDate(monday.getDate() + 6)
    sunday.setHours(23, 59, 59, 999)
    
    return {
      start: monday.toISOString().split('T')[0],
      end: sunday.toISOString().split('T')[0]
    }
  }
  
  // 获取本月时间范围（往前推 30 天）
  const getMonthRange = (): { start: string; end: string } => {
    const mockDate = new Date(MOCK_TODAY.value)
    const start = new Date(mockDate)
    start.setDate(mockDate.getDate() - 29)
    start.setHours(0, 0, 0, 0)
    
    const end = new Date(mockDate)
    end.setHours(23, 59, 59, 999)
    
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0]
    }
  }
  
  return {
    MOCK_TODAY,
    setMockToday,
    getMockToday,
    formatDate,
    getYesterday,
    getLastWeek,
    getLastMonth,
    getTodayRange,
    getWeekRange,
    getMonthRange
  }
})