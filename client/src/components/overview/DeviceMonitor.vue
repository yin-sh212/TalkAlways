<template>
  <n-grid :cols="2" :x-gap="16" :y-gap="16" class="device-grid">
    <n-grid-item>
      <n-card title="设备运行状态" :bordered="false" content-style="padding: 20px;">
        <template #header-extra>
          <n-tag :type="deviceStats.healthScore > 80 ? 'success' : 'warning'" size="small">
            健康度：{{ deviceStats.healthScore }}%
          </n-tag>
        </template>
        <n-skeleton v-if="loading" :rows="4" />
        <template v-else>
          <n-space vertical :size="16">
            <div class="device-stat-item">
              <div class="stat-header">
                <n-icon size="20" color="#52c41a"><CheckCircle /></n-icon>
                <span class="stat-label">正常运行</span>
              </div>
              <div class="stat-value success">{{ deviceStats.normalCount }}</div>
              <n-progress
                :percentage="Math.round(deviceStats.normalCount / deviceStats.totalCount * 100)"
                :color="'#52c41a'"
                :show-indicator="false"
              />
            </div>
            
            <div class="device-stat-item">
              <div class="stat-header">
                <n-icon size="20" color="#f5222d"><Alert /></n-icon>
                <span class="stat-label">异常告警</span>
              </div>
              <div class="stat-value danger">{{ deviceStats.abnormalCount }}</div>
              <n-progress
                :percentage="Math.round(deviceStats.abnormalCount / deviceStats.totalCount * 100)"
                :color="'#f5222d'"
                :show-indicator="false"
              />
            </div>
            
            <div class="device-stat-item">
              <div class="stat-header">
                <n-icon size="20" color="#faad14"><Warning /></n-icon>
                <span class="stat-label">离线设备</span>
              </div>
              <div class="stat-value warning">{{ deviceStats.offlineCount }}</div>
              <n-progress
                :percentage="Math.round(deviceStats.offlineCount / deviceStats.totalCount * 100)"
                :color="'#faad14'"
                :show-indicator="false"
              />
            </div>
            
            <div class="device-stat-item">
              <div class="stat-header">
                <n-icon size="20" color="#18a058"><Layers /></n-icon>
                <span class="stat-label">设备总数</span>
              </div>
              <div class="stat-value">{{ deviceStats.totalCount }}</div>
            </div>
          </n-space>
        </template>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card title="设备类型分布" :bordered="false" content-style="padding: 20px;">
        <n-skeleton v-if="loading" :rows="4" />
        <template v-else>
          <div ref="deviceChartRef" class="device-chart-container"></div>
        </template>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { getBasePieChartConfig } from '@/utils/echarts-config'
import { getMeters } from '@/api/query'
import { CheckmarkCircleOutline as CheckCircle } from '@vicons/ionicons5'
import { AlertOutline as Alert } from '@vicons/ionicons5'
import { WarningOutline as Warning } from '@vicons/ionicons5'
import { LayersOutline as Layers } from '@vicons/ionicons5'

interface DeviceStats {
  totalCount: number
  normalCount: number
  abnormalCount: number
  offlineCount: number
  healthScore: number
}

interface Props {
  loading: boolean
  deviceStats: DeviceStats
}

const props = defineProps<Props>()

const deviceChartRef = ref<HTMLElement | null>(null)
let deviceChart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

// 初始化设备类型分布图
const initDeviceChart = async () => {
  try {
    if (!deviceChartRef.value) return
    
    // 销毁旧实例
    if (deviceChart) {
      deviceChart.dispose()
      deviceChart = null
    }
    
    // 获取数据
    const meterData = await getMeterTypeDistribution()
    
    // 使用公共配置创建图表
    deviceChart = echarts.init(deviceChartRef.value)
    const option = getBasePieChartConfig(
      Array.from(meterData.entries()).map(([name, value]) => ({
        name,
        value
      }))
    )
    
    deviceChart.setOption(option)
  } catch (error) {
    console.error('[DeviceMonitor] 初始化图表失败:', error)
  }
}

// 获取监测点数据并按设备类型聚合
const getMeterTypeDistribution = async (): Promise<Map<string, number>> => {
  try {
    const response = await getMeters()
    const meters = response.data?.data || []
    
    // 按设备类型聚合
    const typeMap = new Map<string, number>()
    meters.forEach((meter: any) => {
      const type = meter.type || '未知'
      typeMap.set(type, (typeMap.get(type) || 0) + 1)
    })
    
    return typeMap
  } catch (error) {
    console.error('[DeviceMonitor] 获取监测点数据失败:', error)
    // 返回默认数据
    return new Map([
      ['空调机组', 45],
      ['照明系统', 38],
      ['电梯设备', 28],
      ['水泵设备', 22],
      ['其他', 17]
    ])
  }
}

// 监听 loading 变化
watch(() => props.loading, (newLoading) => {
  if (!newLoading) {
    nextTick(() => {
      initDeviceChart()
    })
  }
})

onMounted(() => {
  // 如果组件挂载时已经不在 loading 状态，延迟初始化
  if (!props.loading) {
    setTimeout(() => {
      initDeviceChart()
    }, 50)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (deviceChart) {
    deviceChart.dispose()
    deviceChart = null
  }
})
</script>

<style scoped lang="scss">
.device-grid {
  .device-stat-item {
    .stat-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      
      .stat-label {
        font-size: 14px;
        color: #666;
      }
    }
    
    .stat-value {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 8px;
      
      &.success {
        color: #52c41a;
      }
      
      &.danger {
        color: #f5222d;
      }
      
      &.warning {
        color: #faad14;
      }
    }
  }
  
  .device-chart-container {
    height: 250px;
    width: 100%;
  }
}
</style>