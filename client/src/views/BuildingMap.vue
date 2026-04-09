<template>
  <div class="building-map-page">
    <n-card title="建筑空间可视化">
      <!-- 顶部控制栏 -->
      <div class="control-bar">
        <n-space>
          <n-select
            v-model:value="selectedBuilding"
            :options="buildingOptions"
            placeholder="选择建筑"
            style="width: 200px"
            @update:value="handleBuildingChange"
          />
          
          <n-select
            v-model:value="selectedFloor"
            :options="floorOptions"
            placeholder="选择楼层"
            style="width: 150px"
            :disabled="!selectedBuilding"
            @update:value="handleFloorChange"
          />
          
          <n-select
            v-model:value="timeRange"
            :options="timeRangeOptions"
            placeholder="时间范围"
            style="width: 120px"
          />
          
          <n-select
            v-model:value="energyType"
            :options="energyTypeOptions"
            placeholder="能耗类型"
            style="width: 120px"
            clearable
          />
          
          <n-divider vertical />
          
          <n-button 
            :type="isEditMode ? 'warning' : 'default'"
            @click="toggleEditMode"
          >
            {{ isEditMode ? '退出编辑' : '编辑模式' }}
          </n-button>
        </n-space>
      </div>

      <!-- 主要内容区 -->
      <div class="main-content" v-if="currentFloor">
        <!-- 左侧平面图 -->
        <div class="plan-container">
          <FloorPlanViewer
            ref="floorPlanRef"
            :floor="currentFloor"
            :spaces="currentSpaces"
            :selected-space="selectedSpace"
            :time-range="timeRange"
            :energy-type="energyType"
            :is-drawing-mode="isDrawingMode"
            :drawing-points="editorDrawingPoints"
            @space-select="handleSpaceSelect"
            @stage-click="handleStageClick"
            @canvas-click="handleCanvasClick"
            @drawing-finish="handleDrawingFinish"
          />
        </div>

        <!-- 右侧面板 -->
        <div class="detail-panel">
          <!-- 编辑模式：显示 SpaceEditor -->
          <SpaceEditor
            v-if="isEditMode"
            ref="spaceEditorRef"
            :floor="currentFloor"
            :spaces="currentSpaces"
            :selected-space="selectedSpace"
            @space-created="handleSpaceCreated"
            @space-deleted="handleSpaceDeleted"
            @drawing-mode-change="handleDrawingModeChange"
          />

          <!-- 查看模式：显示空间详情 -->
          <n-card v-else-if="selectedSpace" title="空间详情" size="small">
            <n-descriptions :column="2" bordered>
              <n-descriptions-item label="名称">
                {{ selectedSpace.name }}
              </n-descriptions-item>
              <n-descriptions-item label="编号">
                {{ selectedSpace.code }}
              </n-descriptions-item>
              <n-descriptions-item label="类型">
                {{ selectedSpace.space_type === 'room' ? '房间' : '区域' }}
              </n-descriptions-item>
              <n-descriptions-item label="面积">
                {{ selectedSpace.area_sqm }}㎡
              </n-descriptions-item>
            </n-descriptions>

            <!-- 能耗数据 -->
            <n-divider title-placement="left">能耗数据</n-divider>
            <n-spin :show="loadingEnergy">
              <n-descriptions :column="2" bordered v-if="spaceEnergyData">
                <n-descriptions-item label="总能耗">
                  {{ spaceEnergyData.total_energy }} kWh
                </n-descriptions-item>
                <n-descriptions-item label="单位面积能耗">
                  {{ spaceEnergyData.energy_per_sqm }} kWh/㎡
                </n-descriptions-item>
                <n-descriptions-item label="监测点数量">
                  {{ spaceEnergyData.meter_count }}
                </n-descriptions-item>
              </n-descriptions>
              <n-empty v-else description="暂无能耗数据" />
            </n-spin>

            <!-- 操作按钮 -->
            <n-space vertical style="margin-top: 16px">
              <n-button type="primary" block @click="viewEnergyTrend">
                查看能耗趋势
              </n-button>
              <n-button block @click="toggleBindingTool">
                {{ showBindingTool ? '关闭' : '管理点位绑定' }}
              </n-button>
              <n-button block @click="clearSpaceSelection">
                返回楼层概览
              </n-button>
            </n-space>
          </n-card>

          <!-- 查看模式：未选择空间时显示楼层统计 -->
          <n-card v-else-if="floorStats" title="楼层统计" size="small">
            <n-statistic label="总空间数" :value="floorStats.total_spaces || 0" />
            <n-divider style="margin: 12px 0" />
            <n-statistic label="高能耗房间" :value="floorStats.high_energy_spaces || 0">
              <template #suffix>
                <n-tag type="warning" size="small">需关注</n-tag>
              </template>
            </n-statistic>
            <n-divider style="margin: 12px 0" />
            <n-statistic label="异常空间" :value="floorStats.abnormal_spaces || 0">
              <template #suffix>
                <n-tag type="error" size="small">告警</n-tag>
              </template>
            </n-statistic>
            <n-divider style="margin: 12px 0" />
            <n-statistic label="活跃告警" :value="floorStats.active_alarms || 0">
              <template #suffix>
                <n-tag type="error" size="small">待处理</n-tag>
              </template>
            </n-statistic>
            <n-divider style="margin: 12px 0" />
            <n-statistic label="总能耗" :value="floorStats.total_energy || 0">
              <template #suffix>kWh</template>
            </n-statistic>
            
            <!-- 快速切换楼层 -->
            <n-divider style="margin: 16px 0 12px 0" />
            <div style="margin-bottom: 8px; font-weight: 500;">快速切换楼层：</div>
            <n-space vertical>
              <n-button 
                v-for="floor in floors" 
                :key="floor.id"
                :type="selectedFloor === floor.id ? 'primary' : 'default'"
                size="small"
                block
                @click="handleQuickFloorSwitch(floor.id)"
              >
                {{ floor.floor_name }}
              </n-button>
            </n-space>
          </n-card>
        </div>
      </div>

      <!-- 下钻分析区（平面图下方） -->
      <div v-if="selectedSpace && !isEditMode" class="analysis-section">
        <!-- 趋势图表 -->
        <n-card v-if="showTrendChart" title="能耗趋势图" size="small" style="margin-bottom: 16px">
          <template #header-extra>
            <n-button text @click="closeTrendChart">关闭</n-button>
          </template>
          <div ref="trendChartRef" style="height: 350px;"></div>
        </n-card>

        <!-- 监测点绑定工具 -->
        <MeterBindingTool 
          v-if="showBindingTool"
          :space="selectedSpace"
          @binding-updated="handleBindingUpdated"
        />
      </div>

      <n-empty v-else description="请选择建筑和楼层" style="margin-top: 40px" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useMessage } from 'naive-ui'
import * as echarts from 'echarts'
import FloorPlanViewer from '@/components/building/FloorPlanViewer.vue'
import SpaceEditor from '@/components/building/SpaceEditor.vue'
import MeterBindingTool from '@/components/building/MeterBindingTool.vue'
import type { Building, Floor, Space } from '@/types/building'

const message = useMessage()

// 状态管理
const selectedBuilding = ref<string>('')
const selectedFloor = ref<string>('')
const timeRange = ref<string>('today')
const energyType = ref<string>('') // 能耗类型筛选
const selectedSpace = ref<Space | null>(null)
const loadingEnergy = ref(false)
const spaceEnergyData = ref<any>(null)
const showTrendChart = ref(false) // 显示趋势图表
const trendChartRef = ref<HTMLElement | null>(null) // 图表容器引用
let trendChartInstance: echarts.ECharts | null = null // 图表实例
const isEditMode = ref(false) // 编辑模式
const isDrawingMode = ref(false) // 绘制模式
const editorDrawingPoints = ref<[number, number][]>([]) // 编辑器中的绘制点
const showBindingTool = ref(false) // 显示绑定工具
const floorStats = ref<any>(null) // 楼层统计数据

// 获取楼层统计数据
const fetchFloorStats = async () => {
  if (!selectedFloor.value) return
  
  try {
    const response = await fetch(`/api/alarm/floor/stats?floor_id=${selectedFloor.value}`)
    const result = await response.json()
    if (result.code === 200) {
      floorStats.value = result.data
    }
  } catch (error) {
    console.error('获取楼层统计失败:', error)
  }
}

// 监听楼层变化,重新获取统计数据
watch(selectedFloor, () => {
  fetchFloorStats()
})

// 监听时间范围和能耗类型变化，重新加载空间数据以更新热力图
watch([timeRange, energyType], async () => {
  if (selectedFloor.value) {
    await loadSpaces(selectedFloor.value)
    // 如果已选择空间，重新加载该空间的能耗数据
    if (selectedSpace.value) {
      await loadSpaceEnergy(selectedSpace.value.id)
    }
  }
})

// 组件引用
const floorPlanRef = ref<any>(null)
const spaceEditorRef = ref<any>(null)

// 数据列表
const buildings = ref<Building[]>([])
const floors = ref<Floor[]>([])
const spaces = ref<Space[]>([])

// 计算属性
const buildingOptions = computed(() =>
  buildings.value.map(b => ({ label: b.name, value: b.id }))
)

const floorOptions = computed(() =>
  floors.value.map(f => ({ label: f.floor_name, value: f.id }))
)

const currentFloor = computed(() =>
  floors.value.find(f => f.id === selectedFloor.value) || null
)

const currentSpaces = computed(() =>
  spaces.value.filter(s => s.floor_id === selectedFloor.value)
)

const timeRangeOptions = [
  { label: '今日', value: 'today' },
  { label: '昨日', value: 'yesterday' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' }
]

const energyTypeOptions = [
  { label: '全部', value: '' },
  { label: '电力', value: 'electricity' },
  { label: '水', value: 'water' },
  { label: '燃气', value: 'gas' }
]

// 加载建筑列表
const loadBuildings = async () => {
  try {
    const response = await fetch('/api/query/buildings')
    if (!response.ok) throw new Error('Network response was not ok')
    const result = await response.json()
    if (result.code === 200) {
      buildings.value = result.data
      
      // 自动选择第一个建筑
      if (buildings.value.length > 0 && !selectedBuilding.value) {
        selectedBuilding.value = buildings.value[0].id
        await handleBuildingChange(selectedBuilding.value)
      }
    } else {
      message.error(result.message || '加载建筑列表失败')
    }
  } catch (error) {
    console.error(error)
    message.error('加载建筑列表失败')
  }
}

// 加载楼层列表
const loadFloors = async (buildingId: string) => {
  try {
    const response = await fetch(`/api/floor/list?building_id=${buildingId}`)
    if (!response.ok) throw new Error('Network response was not ok')
    const result = await response.json()
    if (result.code === 200) {
      floors.value = result.data
      
      // 自动选择第一层
      if (floors.value.length > 0 && !selectedFloor.value) {
        selectedFloor.value = floors.value[0].id
        await handleFloorChange(selectedFloor.value)
      }
    } else {
      message.error(result.message || '加载楼层列表失败')
    }
  } catch (error) {
    console.error(error)
    message.error('加载楼层列表失败')
  }
}

// 加载空间列表
const loadSpaces = async (floorId: string) => {
  try {
    const response = await fetch(`/api/space/list?floor_id=${floorId}`)
    if (!response.ok) throw new Error('Network response was not ok')
    const result = await response.json()
    if (result.code === 200) {
      spaces.value = result.data
    } else {
      message.error(result.message || '加载空间列表失败')
    }
  } catch (error) {
    console.error(error)
    message.error('加载空间列表失败')
  }
}

// 事件处理
const handleBuildingChange = (value: string) => {
  selectedFloor.value = ''
  selectedSpace.value = null
  spaceEnergyData.value = null
  loadFloors(value)
}

const handleFloorChange = (value: string) => {
  selectedSpace.value = null
  spaceEnergyData.value = null
  loadSpaces(value)
}

const handleSpaceSelect = async (space: Space) => {
  selectedSpace.value = space
  await loadSpaceEnergy(space.id)
}

const handleStageClick = () => {
  selectedSpace.value = null
  spaceEnergyData.value = null
}

// 清除空间选择，返回楼层概览
const clearSpaceSelection = () => {
  selectedSpace.value = null
  spaceEnergyData.value = null
  showTrendChart.value = false
  showBindingTool.value = false
  if (trendChartInstance) {
    trendChartInstance.dispose()
    trendChartInstance = null
  }
}

// 快速切换楼层
const handleQuickFloorSwitch = async (floorId: string) => {
  selectedFloor.value = floorId
  await handleFloorChange(floorId)
  message.success(`已切换到 ${floors.value.find(f => f.id === floorId)?.floor_name}`)
}

// 管理点位绑定
const unbindMeters = () => {
  message.info('点位绑定功能开发中')
}

// 切换编辑模式
const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value
  if (!isEditMode.value) {
    // 退出编辑模式时，重置绘制状态
    isDrawingMode.value = false
    selectedSpace.value = null
  }
  message.info(isEditMode.value ? '已进入编辑模式' : '已退出编辑模式')
}

// 处理绘制模式变化
const handleDrawingModeChange = (drawing: boolean) => {
  isDrawingMode.value = drawing
}

// 处理画布点击（添加顶点）
const handleCanvasClick = (x: number, y: number) => {
  if (isDrawingMode.value && spaceEditorRef.value) {
    // 调用 SpaceEditor 的方法添加顶点
    spaceEditorRef.value.addPoint(x, y)
    // 同步更新绘制点用于显示 - 使用 .value 访问 ref
    editorDrawingPoints.value = [...spaceEditorRef.value.drawingPoints]
  }
}

// 处理完成绘制
const handleDrawingFinish = () => {
  if (spaceEditorRef.value) {
    spaceEditorRef.value.finishDrawing()
    // 清空绘制点显示
    editorDrawingPoints.value = []
  }
}

// 处理空间创建成功
const handleSpaceCreated = (space: Space) => {
  // 重新加载空间列表
  if (selectedFloor.value) {
    loadSpaces(selectedFloor.value)
  }
  message.success('空间创建成功')
}

// 处理空间删除成功
const handleSpaceDeleted = (spaceId: string) => {
  // 从列表中移除
  spaces.value = spaces.value.filter(s => s.id !== spaceId)
  if (selectedSpace.value?.id === spaceId) {
    selectedSpace.value = null
    spaceEnergyData.value = null
  }
  message.success('空间删除成功')
}

// 加载空间能耗
const loadSpaceEnergy = async (spaceId: string) => {
  loadingEnergy.value = true
  try {
    const params = new URLSearchParams({
      time_range: timeRange.value
    })
    if (energyType.value) {
      params.append('energy_type', energyType.value)
    }
    
    const response = await fetch(
      `/api/space-energy/${spaceId}?${params.toString()}`
    )
    const result = await response.json()
    if (result.code === 200) {
      spaceEnergyData.value = result.data
    }
  } catch (error) {
    message.error('加载能耗数据失败')
  } finally {
    loadingEnergy.value = false
  }
}

// 查看能耗趋势
const viewEnergyTrend = async () => {
  if (!selectedSpace.value) return
  
  showTrendChart.value = true
  await nextTick()
  
  try {
    const params = new URLSearchParams({
      time_range: timeRange.value
    })
    if (energyType.value) {
      params.append('energy_type', energyType.value)
    }
    
    const response = await fetch(
      `/api/space-energy/${selectedSpace.value.id}/trend?${params.toString()}`
    )
    const result = await response.json()
    
    if (result.code === 200 && trendChartRef.value) {
      const chartData = result.data
      
      // 初始化或更新图表
      if (!trendChartInstance) {
        trendChartInstance = echarts.init(trendChartRef.value)
      }
      
      const option = {
        title: {
          text: '能耗趋势',
          left: 'center',
          textStyle: { fontSize: 14 }
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: chartData.series.map((s: any) => s.name),
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: chartData.categories
        },
        yAxis: {
          type: 'value',
          name: '能耗值'
        },
        series: chartData.series
      }
      
      trendChartInstance.setOption(option)
    } else {
      message.error('加载趋势数据失败')
    }
  } catch (error) {
    console.error(error)
    message.error('加载趋势数据失败')
  }
}

// 关闭趋势图表
const closeTrendChart = () => {
  showTrendChart.value = false
  if (trendChartInstance) {
    trendChartInstance.dispose()
    trendChartInstance = null
  }
}

// 切换绑定工具显示
const toggleBindingTool = () => {
  showBindingTool.value = !showBindingTool.value
}

// 处理绑定更新
const handleBindingUpdated = () => {
  message.success('点位绑定更新成功')
}

// 初始化
onMounted(() => {
  loadBuildings()
})
</script>

<style scoped>
.building-map-page {
  padding: 20px;
}

.control-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 4px;
}

.main-content {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}

.plan-container {
  flex: 1;
  min-width: 0;
}

.detail-panel {
  width: 350px;
  flex-shrink: 0;
}

.analysis-section {
  margin-top: 20px;
  padding: 16px;
  background: #fafafa;
  border-radius: 4px;
}
</style>
