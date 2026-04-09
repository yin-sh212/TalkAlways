<template>
  <div class="floor-plan-viewer">
    <v-stage
      ref="stageRef"
      :config="stageConfig"
      @mousedown="handleStageMouseDown"
      @touchstart="handleStageMouseDown"
      @wheel="handleWheel"
      @dragend="handleDragEnd"
    >
      <!-- 底图 -->
      <v-layer>
        <v-image :config="imageConfig" />
      </v-layer>

      <!-- 空间区块层 -->
      <v-layer>
        <v-group
          v-for="space in spaces"
          :key="space.id"
          :config="{
            id: space.id,
            draggable: false,
            listening: !isDrawingMode
          }"
        >
          <!-- 多边形 - 使用 v-shape 绘制自定义路径 -->
          <v-shape
            :config="{
              sceneFunc: (context: any, shape: any) => {
                const points = flattenPolygon(space.polygon)
                context.beginPath()
                context.moveTo(points[0], points[1])
                for (let i = 2; i < points.length; i += 2) {
                  context.lineTo(points[i], points[i + 1])
                }
                context.closePath()
                context.fillStrokeShape(shape)
              },
              fill: getSpaceColor(space),
              stroke: getSpaceStrokeColor(space),
              strokeWidth: getSpaceStrokeWidth(space),
              opacity: hoveredSpace?.id === space.id ? 0.7 : getSpaceOpacity(space),
              listening: !isDrawingMode,
              shadowColor: isAbnormalSpace(space) ? 'red' : 'transparent',
              shadowBlur: isAbnormalSpace(space) ? 15 : 0,
              shadowOffset: { x: 0, y: 0 },
              shadowOpacity: isAbnormalSpace(space) ? 0.8 : 0,
              // 告警空间添加闪烁效果
              dash: hasActiveAlarm(space) ? [10, 5] : []
            }"
            @mouseenter="handleSpaceHover(space)"
            @mouseleave="handleSpaceLeave"
            @click="handleSpaceClick(space)"
          />
          
          <!-- 空间标签 -->
          <v-label
            :config="{
              x: space.center_x - 30,
              y: space.center_y - 15,
              opacity: 0.8
            }"
          >
            <v-tag
              :config="{
                fill: 'white',
                cornerRadius: 3,
                padding: 5
              }"
            />
            <v-text
              :config="{
                text: space.code,
                fontSize: 12,
                fill: '#333',
                width: 60,
                align: 'center'
              }"
            />
          </v-label>
        </v-group>
        
        <!-- 绘制模式：显示临时顶点和连线 -->
        <template v-if="isDrawingMode && drawingPoints.length > 0">
          <!-- 连线 -->
          <v-line
            :config="{
              points: flattenDrawingPoints(),
              stroke: '#52c41a',
              strokeWidth: 2,
              dash: [5, 5]
            }"
          />
          <!-- 顶点 -->
          <v-circle
            v-for="(point, index) in drawingPoints"
            :key="index"
            :config="{
              x: point[0],
              y: point[1],
              radius: 5,
              fill: '#52c41a',
              stroke: 'white',
              strokeWidth: 2
            }"
          />
        </template>
      </v-layer>
    </v-stage>

    <!-- 缩放控制按钮 -->
    <div class="zoom-controls">
      <n-button size="small" @click="handleZoomIn">
        <template #icon>+</template>
      </n-button>
      <n-button size="small" @click="handleZoomOut">
        <template #icon>-</template>
      </n-button>
      <n-button size="small" @click="handleResetZoom">
        重置
      </n-button>
      <span class="zoom-level">{{ Math.round((scale || 1) * 100) }}%</span>
    </div>

    <!-- 热力图图例 -->
    <div class="heat-legend">
      <div class="legend-title">能耗等级</div>
      <div class="legend-item">
        <span class="legend-color" style="background: #52c41a"></span>
        <span>正常 (&lt;2 kWh/㎡)</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #faad14"></span>
        <span>偏高 (2-5 kWh/㎡)</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #ff7a45"></span>
        <span>较高 (5-10 kWh/㎡)</span>
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #ff4d4f"></span>
        <span>异常 (&gt;10 kWh/㎡)</span>
      </div>
    </div>

    <!-- 悬浮提示框 -->
    <div
      v-if="hoveredSpace && tooltipVisible"
      class="space-tooltip"
      :style="{ left: tooltipPosition.x + 'px', top: tooltipPosition.y + 'px' }"
    >
      <div class="tooltip-title">{{ hoveredSpace.name }}</div>
      <div class="tooltip-info">编号: {{ hoveredSpace.code }}</div>
      <div class="tooltip-info">面积: {{ hoveredSpace.area_sqm }}㎡</div>
      <div class="tooltip-info" v-if="hoveredSpaceEnergy">
        能耗: {{ hoveredSpaceEnergy.total_energy }} kWh
      </div>
      <div class="tooltip-info" v-if="hoveredSpaceEnergy">
        单位能耗: {{ hoveredSpaceEnergy.energy_per_sqm }} kWh/㎡
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { debounce } from 'lodash-es'
import type { Floor, Space } from '@/types/building'

interface Props {
  floor: Floor | null
  spaces: Space[]
  selectedSpace?: Space | null
  timeRange?: string
  energyType?: string
  isDrawingMode?: boolean
  drawingPoints?: [number, number][]
}

// FloorPlanViewer Props
const props = withDefaults(defineProps<Props>(), {
  timeRange: 'today',
  energyType: '',
  isDrawingMode: false,
  drawingPoints: () => []
})

// 解构 selectedSpace 以便在 script 中使用
const { selectedSpace } = props

const emit = defineEmits<{
  (e: 'space-select', space: Space): void
  (e: 'stage-click'): void
  (e: 'canvas-click', x: number, y: number): void
  (e: 'drawing-finish'): void
}>()

// Stage 引用
const stageRef = ref<any>(null)

// 缩放状态
const scale = ref(1)
const position = ref({ x: 0, y: 0 })

// Stage 配置
const stageConfig = computed(() => ({
  width: props.floor?.width || 800,
  height: props.floor?.height || 600,
  scaleX: scale.value,
  scaleY: scale.value,
  x: position.value.x,
  y: position.value.y,
  draggable: true
}))

// 底图配置
const imageConfig = computed(() => ({
  image: props.floor?.image_url ? new Image() : null,
  x: 0,
  y: 0,
  width: props.floor?.width || 800,
  height: props.floor?.height || 600
}))

// 加载底图
watch(() => props.floor?.image_url, (url) => {
  if (url) {
    const img = new Image()
    img.src = url
    img.onload = () => {
      // 图片加载完成
    }
  }
}, { immediate: true })

// 状态管理
const hoveredSpace = ref<Space | null>(null)
const tooltipVisible = ref(false)
const tooltipPosition = ref({ x: 0, y: 0 })
const hoveredSpaceEnergy = ref<any>(null)
const spaceAlarms = ref<Record<string, any[]>>({}) // 空间告警数据

// 带过期时间的缓存结构
interface CacheItem {
  data: any
  timestamp: number
}
const CACHE_TTL = 5 * 60 * 1000 // 缓存有效期 5 分钟
const energyCache = new Map<string, CacheItem>() // 能耗数据缓存

// 获取空间活跃告警
const fetchSpaceAlarms = async () => {
  if (!props.floor?.id) return
  
  try {
    const response = await fetch(`/api/alarm/space/active-alarms?floor_id=${props.floor.id}`)
    const result = await response.json()
    if (result.code === 200) {
      spaceAlarms.value = result.data
    }
  } catch (error) {
    console.error('获取空间告警失败:', error)
  }
}

// 监听楼层变化,重新获取告警数据
watch(() => props.floor?.id, () => {
  fetchSpaceAlarms()
}, { immediate: true })

// 展平多边形坐标
const flattenPolygon = (polygon: number[][]): number[] => {
  return polygon.flat()
}

// 展平绘制点（用于 v-line）
const flattenDrawingPoints = (): number[] => {
  return props.drawingPoints.flat()
}

// 获取空间颜色（基于能耗和告警）
const getSpaceColor = (space: Space): string => {
  // 有活跃告警的空间显示红色
  if (spaceAlarms.value[space.id] && spaceAlarms.value[space.id].length > 0) {
    return '#ff4d4f'
  }
  
  if (!space.energy_per_sqm) return '#1890ff'
  
  const value = space.energy_per_sqm
  if (value < 2) return '#52c41a' // 绿色 - 低能耗
  if (value < 5) return '#faad14' // 黄色 - 中等
  if (value < 10) return '#ff7a45' // 橙色 - 较高
  return '#ff4d4f' // 红色 - 高能耗
}

// 获取空间边框颜色
const getSpaceStrokeColor = (space: Space): string => {
  return selectedSpace?.id === space.id ? '#ff4d4f' : '#1890ff'
}

// 获取空间边框宽度
const getSpaceStrokeWidth = (space: Space): number => {
  return selectedSpace?.id === space.id ? 3 : 2
}

// 获取空间透明度
const getSpaceOpacity = (space: Space): number => {
  return 0.3
}

// 判断空间是否有活跃告警
const hasActiveAlarm = (space: Space): boolean => {
  return !!(spaceAlarms.value[space.id] && spaceAlarms.value[space.id].length > 0)
}

// 判断空间是否异常（有告警或能耗过高）
const isAbnormalSpace = (space: Space): boolean => {
  // 有活跃告警
  if (hasActiveAlarm(space)) {
    return true
  }
  // 能耗异常
  return !!(space.energy_per_sqm && space.energy_per_sqm > 10)
}

// 获取空间能耗数据的异步函数
const fetchSpaceEnergy = async (space: Space) => {
  // 检查缓存（包含能耗类型）
  const cacheKey = `${space.id}_${props.timeRange}_${props.energyType || 'all'}`
  const cachedItem = energyCache.get(cacheKey)
  
  // 检查缓存是否存在且未过期
  if (cachedItem && (Date.now() - cachedItem.timestamp) < CACHE_TTL) {
    hoveredSpaceEnergy.value = cachedItem.data
    return
  }
  
  // 缓存已过期或不存在，清除旧缓存
  if (cachedItem) {
    energyCache.delete(cacheKey)
  }
  
  // 获取该空间能耗数据
  try {
    const params = new URLSearchParams({
      time_range: props.timeRange
    })
    if (props.energyType) {
      params.append('energy_type', props.energyType)
    }
    
    const response = await fetch(
      `/api/space-energy/${space.id}?${params.toString()}`
    )
    const result = await response.json()
    if (result.code === 200) {
      hoveredSpaceEnergy.value = result.data
      // 存入缓存并记录时间戳
      energyCache.set(cacheKey, {
        data: result.data,
        timestamp: Date.now()
      })
    }
  } catch (error) {
    console.error('获取空间能耗失败:', error)
  }
}

// 创建防抖版本的能耗获取函数（300ms 延迟）
const debouncedFetchSpaceEnergy = debounce((space: Space) => {
  fetchSpaceEnergy(space)
}, 300)

// 事件处理
const handleSpaceHover = (space: Space) => {
  // 绘制模式下不显示悬浮提示
  if (props.isDrawingMode) return
  
  hoveredSpace.value = space
  tooltipVisible.value = true
  
  // 使用防抖函数获取能耗数据，避免频繁请求
  debouncedFetchSpaceEnergy(space)
}

const handleSpaceLeave = () => {
  hoveredSpace.value = null
  tooltipVisible.value = false
  hoveredSpaceEnergy.value = null
}

const handleSpaceClick = (space: Space) => {
  emit('space-select', space)
}

const handleStageMouseDown = (e: any) => {
  // 如果在绘制模式下，任何点击都添加顶点
  if (props.isDrawingMode) {
    const stage = e.target.getStage()
    const pointer = stage.getPointerPosition()
    // 考虑缩放和平移，计算实际坐标
    const x = (pointer.x - position.value.x) / scale.value
    const y = (pointer.y - position.value.y) / scale.value
    
    // 右键或双击结束绘制
    if (e.evt.button === 2 || e.evt.detail === 2) {
      emit('drawing-finish')
      return
    }
    
    emit('canvas-click', x, y)
    return
  }
  
  // 非绘制模式：点击空白处取消选择
  if (e.target === e.target.getStage()) {
    emit('stage-click')
  }
}

// 滚轮缩放
const handleWheel = (e: any) => {
  e.evt.preventDefault()
  
  const stage = stageRef.value?.getNode()
  if (!stage) return
  
  const oldScale = scale.value
  const pointer = stage.getPointerPosition()
  
  const mousePointTo = {
    x: (pointer.x - position.value.x) / oldScale,
    y: (pointer.y - position.value.y) / oldScale
  }
  
  // 计算新缩放比例
  const delta = e.evt.deltaY > 0 ? 0.9 : 1.1
  const newScale = Math.max(0.2, Math.min(5, oldScale * delta))
  
  scale.value = newScale
  position.value = {
    x: pointer.x - mousePointTo.x * newScale,
    y: pointer.y - mousePointTo.y * newScale
  }
}

// 缩放控制
const handleZoomIn = () => {
  scale.value = Math.min(5, scale.value * 1.2)
}

const handleZoomOut = () => {
  scale.value = Math.max(0.2, scale.value / 1.2)
}

const handleResetZoom = () => {
  scale.value = 1
  position.value = { x: 0, y: 0 }
}

// Stage 拖拽结束事件
const handleDragEnd = () => {
  const stage = stageRef.value?.getNode()
  if (stage) {
    position.value = {
      x: stage.x(),
      y: stage.y()
    }
  }
}

// 更新鼠标位置
onMounted(() => {
  document.addEventListener('mousemove', (e) => {
    if (tooltipVisible.value) {
      tooltipPosition.value = {
        x: e.clientX + 15,
        y: e.clientY + 15
      }
    }
  })
})

// 组件卸载时清理
onUnmounted(() => {
  // 取消防抖函数，避免内存泄漏
  debouncedFetchSpaceEnergy.cancel()
  // 清除缓存，释放内存
  energyCache.clear()
})
</script>

<style scoped>
.floor-plan-viewer {
  position: relative;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  overflow: hidden;
  background: #fafafa;
}

.space-tooltip {
  position: fixed;
  z-index: 1000;
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  min-width: 200px;
  pointer-events: none;
}

.zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 100;
  background: white;
  padding: 8px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.zoom-level {
  text-align: center;
  font-size: 12px;
  color: #666;
}

.tooltip-title {
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 8px;
  color: #262626;
}

.tooltip-info {
  font-size: 12px;
  color: #595959;
  margin: 4px 0;
}

.heat-legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: white;
  padding: 12px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 100;
  min-width: 160px;
}

.legend-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #666;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  flex-shrink: 0;
}
</style>