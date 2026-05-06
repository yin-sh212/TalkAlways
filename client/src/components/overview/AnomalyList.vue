<template>
  <n-card title="实时异常/报警（最新 5 条）" :bordered="false" content-style="padding: 12px;">
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
        >
          <div class="timeline-content">
            <span class="timeline-text">{{ item.buildingName }} - {{ item.type }}</span>
            <n-button 
              text 
              size="small" 
              type="primary"
              class="analyze-btn"
              @click="handleAnalyze(item)"
            >
              分析
            </n-button>
          </div>
          <div v-if="item.description" class="timeline-description">{{ item.description }}</div>
        </n-timeline-item>
      </n-timeline>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { ChevronForwardOutline as ArrowRight } from '@vicons/ionicons5'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'

const router = useRouter()
const message = useMessage()

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

// 分析具体异常
const handleAnalyze = (item: AnomalyItem) => {
  // 使用 item.id 作为告警 ID（应该是数字类型的字符串）
  const alarmId = item.id
  
  // 如果 id 不是纯数字，尝试从 description 或其他字段提取
  // 但根据 Overview.vue 的实现，id 应该是 `${record.building_id}_${record.timestamp}` 格式
  // 这种情况下我们需要通过时间和建筑来定位告警
  
  const buildingId = item.buildingId || ''
  const alarmTime = item.time
  
  // 跳转到告警页面，传递查询参数高亮指定告警
  router.push({
    path: '/alarm',
    query: {
      highlight_id: alarmId,
      expand_detail: 'true',
      building_id: buildingId,
      alarm_time: alarmTime
    }
  })
  
  message.success(`正在查看告警详情`)
}

// 按时间倒序排列的异常列表
const sortedAnomalyList = computed(() => {
  return [...props.anomalyList].sort((a, b) => {
    // 将时间字符串转换为 Date 对象进行比较
    const dateA = new Date(a.time)
    const dateB = new Date(b.time)
    // 倒序排列，最新的在前面
    return dateB.getTime() - dateA.getTime()
  }).slice(0, 5) // 只取前 5 条
})
</script>

<style scoped lang="scss">
.refresh-time {
  font-size: 13px;
  color: #999;
}

.simulate-time {
  font-size: 13px;
  color: #999;
  margin-right: 10px;
}

.timeline-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  
  .timeline-text {
    flex: 1;
    font-weight: 500;
    font-size: 15px;
  }
  
  .analyze-btn {
    margin-left: 12px;
    flex-shrink: 0;
    font-size: 14px;
  }
}

.timeline-description {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-color-secondary);
  line-height: 1.5;
}
:deep(.n-timeline-item-content__time) {
  font-size: 13px;
}
</style>