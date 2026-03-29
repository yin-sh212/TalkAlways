import { defineStore } from 'pinia'
import { ref } from 'vue'

// 建筑信息类型定义
export interface BuildingInfo {
  id: string
  name: string
  type?: string
  area?: number
  [key: string]: any // 允许其他字段
}

// 固定的建筑列表数据（写死在前端，不再请求后端）
const FIXED_BUILDINGS: BuildingInfo[] = [
  { id: 'Eagle_education_Cassie', name: 'Eagle_education_Cassie', type: '教学楼', area: 0 },
  { id: 'Eagle_education_Wesley', name: 'Eagle_education_Wesley', type: '教学楼', area: 0 },
  { id: 'Eagle_office_Francis', name: 'Eagle_office_Francis', type: '办公楼', area: 0 },
  { id: 'Eagle_office_Henriette', name: 'Eagle_office_Henriette', type: '办公楼', area: 0 },
  { id: 'Eagle_office_Nereida', name: 'Eagle_office_Nereida', type: '办公楼', area: 0 },
  { id: 'Fox_assembly_Adrianne', name: 'Fox_assembly_Adrianne', type: '公共娱乐场所', area: 0 },
  { id: 'Fox_assembly_Renna', name: 'Fox_assembly_Renna', type: '公共娱乐场所', area: 0 },
  { id: 'Fox_education_Jacqueline', name: 'Fox_education_Jacqueline', type: '教学楼', area: 0 },
  { id: 'Fox_lodging_Helen', name: 'Fox_lodging_Helen', type: '住宅区', area: 0 },
  { id: 'Fox_lodging_Wallace', name: 'Fox_lodging_Wallace', type: '住宅区', area: 0 },
]

export const useBuildingStore = defineStore('building', () => {
  // 建筑列表 - 存储建筑对象
  const buildings = ref<BuildingInfo[]>(FIXED_BUILDINGS)
  
  // 当前选中的建筑 ID（只存字符串 ID）
  const currentBuildingId = ref<string>('')
  
  // 缓存标记：始终为 true，因为数据是写死的
  const isLoaded = ref<boolean>(true)

  // 获取建筑列表（直接返回固定数据）
  const fetchBuildings = async (forceRefresh: boolean = false) => {
    // 数据已经初始化在 buildings 中，直接返回成功
    // 如果有第一个建筑且未设置当前建筑，默认选择第一个
    if (buildings.value.length > 0 && !currentBuildingId.value) {
      currentBuildingId.value = buildings.value[0].id
    }
    
    return { success: true, cached: true }
  }

  // 设置当前建筑 ID
  const setCurrentBuildingId = (buildingId: string) => {
    currentBuildingId.value = buildingId
  }

  // 重置建筑信息（包括缓存状态）
  const resetBuildings = () => {
    buildings.value = FIXED_BUILDINGS
    currentBuildingId.value = ''
    isLoaded.value = true
  }
  
  // 清除缓存（用于用户登出等场景）
  const clearCache = () => {
    isLoaded.value = true
  }

  return {
    buildings,
    currentBuildingId,
    isLoaded,
    fetchBuildings,
    setCurrentBuildingId,
    resetBuildings,
    clearCache
  }
})
