import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as queryApi from '@/api/query'

// 建筑信息类型定义
export interface BuildingInfo {
  id: string
  name: string
  type?: string
  area?: number
  [key: string]: any // 允许其他字段
}

export const useBuildingStore = defineStore('building', () => {
  // 建筑列表 - 存储建筑对象
  const buildings = ref<BuildingInfo[]>([])
  
  // 当前选中的建筑 ID（只存字符串 ID）
  const currentBuildingId = ref<string>('')

  // 获取建筑列表
  const fetchBuildings = async () => {
    try {
      const response = await queryApi.getBuildings()
      const data = response.data.data || []
      
      // 兼容两种数据格式：字符串数组或对象数组
      if (data.length > 0 && typeof data[0] === 'string') {
        // 如果是字符串数组，转换为对象数组
        buildings.value = data.map((id: string) => ({ id, name: `建筑${id}` }))
      } else {
        // 如果是对象数组，直接使用（需要类型断言）
        buildings.value = data as unknown as BuildingInfo[]
      }
      
      // 如果有建筑且未设置当前建筑，默认选择第一个
      if (buildings.value.length > 0 && !currentBuildingId.value) {
        // 提取第一个建筑的 ID
        currentBuildingId.value = buildings.value[0].id
      }
      
      return { success: true }
    } catch (error: any) {
      console.error('获取建筑列表失败:', error)
      return { success: false, message: error.message || '获取建筑列表失败' }
    }
  }

  // 设置当前建筑 ID
  const setCurrentBuildingId = (buildingId: string) => {
    currentBuildingId.value = buildingId
  }

  // 重置建筑信息
  const resetBuildings = () => {
    buildings.value = []
    currentBuildingId.value = ''
  }

  return {
    buildings,
    currentBuildingId,
    fetchBuildings,
    setCurrentBuildingId,
    resetBuildings
  }
})
