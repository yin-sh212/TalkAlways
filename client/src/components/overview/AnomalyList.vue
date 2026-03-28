<template>
  <n-card title="实时异常/报警（最新 5 条）" :bordered="false" content-style="padding: 20px;">
    <template #header-extra>
      <n-space align="center">
        <span v-if="currentSimulateTime" class="simulate-time">
          📡 模拟时间：{{ currentSimulateTime }}
        </span>
        <span class="refresh-time">最后更新：{{ lastUpdateTime }}</span>
        <n-button text size="small" @click="handleViewAll">
          查看全部
          <template #icon>
            <n-icon :component="ArrowRight" />
          </template>
        </n-button>
      </n-space>
    </template>
    
    <n-skeleton v-if="loading" :rows="5" />
    <template v-else>
      <n-empty v-if="anomalyList.length === 0" description="暂无异常数据" />
      <n-timeline v-else>
        <n-timeline-item
          v-for="item in sortedAnomalyList"
          :key="item.id"
          :type="getTypeTagType(item.type)"
          :time="item.time"
          :content="`${item.buildingName} - ${item.type}`"
          :description="item.description"
        />
      </n-timeline>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { ChevronForwardOutline as ArrowRight } from '@vicons/ionicons5'
import { computed } from 'vue'

interface AnomalyItem {
  id: string
  time: string
  buildingName: string
  type: string
  status: 'pending' | 'processing' | 'resolved'
  buildingId?: string
  meterId?: string
  electricity?: number
  ambientTemp?: number
  description?: string
  timeRange?: {
    start: string
    end: string
  }
}

interface Props {
  loading: boolean
  anomalyList: AnomalyItem[]
  lastUpdateTime: string
  currentSimulateTime?: string
}

const props = withDefaults(defineProps<Props>(), {
  currentSimulateTime: ''
})

// 定义事件
const emit = defineEmits<{
  (e: 'view-all'): void
}>()

// 获取异常类型对应的标签颜色
const getTypeTagType = (type: string) => {
  if (type.includes('突增')) return 'error'
  if (type.includes('突降')) return 'warning'
  if (type.includes('离线')) return 'info'
  return 'default'
}

// 查看全部
const handleViewAll = () => {
  emit('view-all')
}

// 按时间倒序排列的异常列表
const sortedAnomalyList = computed(() => {
  return [...props.anomalyList].sort((a, b) => {
    // 将时间字符串转换为Date对象进行比较
    const dateA = new Date(a.time)
    const dateB = new Date(b.time)
    // 倒序排列，最新的在前面
    return dateB.getTime() - dateA.getTime()
  }).slice(0, 5) // 只取前5条
})
</script>

<style scoped lang="scss">
.refresh-time {
  font-size: 12px;
  color: #999;
}

.simulate-time {
  font-size: 12px;
  color: #999;
  margin-right: 10px;
}

</style>