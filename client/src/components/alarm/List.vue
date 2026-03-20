<template>
  <n-card title="告警列表" :bordered="false" content-style="padding: 16px;">
    <template #header-extra>
      <n-space>
        <n-button size="small" type="primary" @click="handleBatchAcknowledge">
          批量确认
        </n-button>
        <n-button size="small" type="success" @click="handleBatchResolve">
          批量解决
        </n-button>
      </n-space>
    </template>
    <n-data-table
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      :row-key="(row) => row.id || row.alarm_id || 'unknown'"
      :checked-row-keys="checkedRowKeys"
      @update:checked-row-keys="onChecked"
      striped
    />
  </n-card>

  <!-- 告警详情弹窗 -->
  <n-modal
    v-model:show="showDetailModal"
    preset="dialog"
    title="告警详情分析"
    style="width: 800px;"
    :positive-text="'关闭'"
    @positive-click="showDetailModal = false"
  >
    <div v-if="detailLoading" style="text-align: center; padding: 40px;">
      <n-spin size="large" description="正在加载告警分析..." />
    </div>
    <div v-else-if="analysisData" class="alarm-detail-content">
      <n-descriptions bordered :column="2">
        <n-descriptions-item label="告警 ID">
          {{ analysisData.alarm_id }}
        </n-descriptions-item>
        <n-descriptions-item label="告警时间">
          {{ formatDateTime(analysisData.start_time) }}
        </n-descriptions-item>
        <n-descriptions-item label="建筑 ID">
          {{ analysisData.building_id }}
        </n-descriptions-item>
        <n-descriptions-item label="告警类型">
          {{ getAlarmTypeName(analysisData.alarm_type) }}
        </n-descriptions-item>
        <n-descriptions-item label="告警级别" :span="2">
          <n-tag :type="getLevelType(analysisData.alarm_level)" size="medium">
            {{ getLevelName(analysisData.alarm_level) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="告警描述" :span="2">
          {{ analysisData.description }}
        </n-descriptions-item>
      </n-descriptions>

      <n-divider title-style="margin-top: 24px;">主要原因</n-divider>
      <div class="detail-section">
        <n-alert type="warning" :title="'根本原因分析'">
          <markdown-renderer :content="analysisData.main_cause" />
        </n-alert>
      </div>

      <n-divider title-style="margin-top: 24px;">影响因素 (TOP 3)</n-divider>
      <div class="detail-section">
        <n-list v-if="analysisData.top_factors && analysisData.top_factors.length > 0">
          <n-list-item v-for="(factor, index) in analysisData.top_factors" :key="index">
            <template #prefix>
              <n-tag :type="getImpactType(factor.impact)" size="medium">
                {{ factor.impact === 'high' ? '高' : factor.impact === 'medium' ? '中' : '低' }}
              </n-tag>
            </template>
            <div>
              <div style="font-weight: 600; margin-bottom: 4px;">
                {{ factor.factor }}: 
                <span v-if="factor.value !== undefined">{{ factor.value }}</span>
                <span v-if="factor.normal !== undefined"> (正常值：{{ factor.normal }})</span>
              </div>
              <div style="color: var(--n-text-color-3); font-size: 14px;">
                {{ factor.description }}
              </div>
            </div>
          </n-list-item>
        </n-list>
        <n-empty v-else description="暂无影响因素数据" />
      </div>

      <n-divider title-style="margin-top: 24px;">快速解决方案</n-divider>
      <div class="detail-section">
        <n-alert type="success" :title="'处理建议'">
          <markdown-renderer :content="analysisData.quick_solution" />
        </n-alert>
      </div>

      <div v-if="analysisData.related_knowledge && analysisData.related_knowledge.length > 0" class="detail-section">
        <n-divider title-style="margin-top: 24px;">相关知识库</n-divider>
        <n-space vertical>
          <n-button 
            v-for="(knowledge, index) in analysisData.related_knowledge" 
            :key="index"
            text 
            type="primary"
            @click="viewKnowledge(knowledge.url)"
          >
            📖 {{ knowledge.title }}
          </n-button>
        </n-space>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h } from 'vue'
import { useMessage } from 'naive-ui'
import type { DataTableColumns, DataTableRowKey } from 'naive-ui'
import { NButton, NTag, NPopconfirm } from 'naive-ui'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'
import * as alarmApi from '@/api/alarm'

const message = useMessage()

interface AlarmItem {
  id: string
  time: string
  buildingName: string
  alarmType: string
  alarmTypeName?: string
  severity: string
  description: string
  status: string
  acknowledgeTime?: string
  resolveTime?: string
}

const props = defineProps<{
  tableData: AlarmItem[]
  loading?: boolean
  pagination?: any
}>()

const emit = defineEmits<{
  (e: 'update', page: number, pageSize: number): void
  (e: 'acknowledge', alarmId: string): void
  (e: 'resolve', alarmId: string): void
  (e: 'batch-acknowledge', alarmIds: string[]): void
  (e: 'batch-resolve', alarmIds: string[]): void
}>()

const checkedRowKeys = ref<DataTableRowKey[]>([])

// 告警详情相关
const showDetailModal = ref(false)
const detailLoading = ref(false)
const analysisData = ref<any>(null)
const currentAlarm = ref<AlarmItem | null>(null)

// 格式化日期时间
const formatDateTime = (datetime: string) => {
  if (!datetime) return ''
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取告警类型名称
const getAlarmTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    energy: '能耗告警',
    equipment: '设备告警',
    environment: '环境告警',
    energy_anomaly: '能耗异常',
    device_fault: '设备故障',
    sensor_error: '传感器异常',
    communication_error: '通信故障',
    threshold_exceeded: '超限告警',
  }
  return typeMap[type] || type
}

// 获取告警级别名称
const getLevelName = (level: number) => {
  const levelMap: Record<number, string> = {
    1: '严重',
    2: '警告',
    3: '提示'
  }
  return levelMap[level] || `级别${level}`
}

// 获取告警级别类型
const getLevelType = (level: number) => {
  const typeMap: Record<number, any> = {
    1: 'error',
    2: 'warning',
    3: 'info'
  }
  return typeMap[level] || 'default'
}

// 获取影响程度类型
const getImpactType = (impact: string) => {
  const typeMap: Record<string, any> = {
    high: 'error',
    medium: 'warning',
    low: 'info'
  }
  return typeMap[impact] || 'default'
}

// 告警级别映射
const severityMap: Record<string, any> = {
  critical: { type: 'error', text: '紧急' },
  major: { type: 'warning', text: '重要' },
  minor: { type: 'info', text: '一般' },
  warning: { type: 'success', text: '提示' }
}

// 状态映射
const statusMap: Record<string, any> = {
  unresolved: { type: 'error', text: '未解决' },
  acknowledged: { type: 'warning', text: '已确认' },
  resolved: { type: 'success', text: '已解决' }
}

// 获取当前告警级别的类型
const getCurrentSeverityType = (severity?: string) => {
  if (!severity) return 'default'
  return severityMap[severity]?.type || 'default'
}

// 表格列定义
const columns: DataTableColumns = [
  {
    type: 'selection',
    disabled: (row: any) => row.status === 'resolved'
  },
  {
    title: '时间',
    key: 'time',
    width: 180,
    sorter: 'default'
  },
  {
    title: '建筑名称',
    key: 'buildingName',
    width: 150,
    sorter: 'default'
  },
  {
    title: '告警类型',
    key: 'alarmTypeName',
    width: 150,
    render: (row: any) => {
      return row.alarmTypeName || row.alarmType || '未知'
    }
  },
  {
    title: '级别',
    key: 'severity',
    width: 100,
    render: (row: any) => {
      const config = severityMap[row.severity] || { type: 'default', text: '未知' }
      return h(NTag, {
        type: config.type as any,
        size: 'small',
        bordered: false
      }, { default: () => config.text })
    }
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) => {
      const config = statusMap[row.status] || { type: 'default', text: '未知' }
      return h(NTag, {
        type: config.type as any,
        size: 'small',
        bordered: false
      }, { default: () => config.text })
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    fixed: 'right',
    render: (row: any) => {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
        // 查看详情按钮
        h(NButton, {
          size: 'small',
          type: 'info',
          onClick: () => handleViewDetail(row)
        }, { default: () => '详情' }),
        
        // 确认按钮
        row.status === 'unresolved' ? h(NButton, {
          size: 'small',
          type: 'primary',
          onClick: () => emit('acknowledge', row.id)
        }, { default: () => '确认' }) : null,
        
        // 解决按钮
        row.status !== 'resolved' ? h(NPopconfirm, {
          onPositiveClick: () => emit('resolve', row.id),
          positiveText: '确定',
          negativeText: '取消'
        }, {
          trigger: () => h(NButton, {
            size: 'small',
            type: 'success',
            disabled: row.status === 'resolved'
          }, { default: () => '解决' }),
          default: () => '确定要解决该告警吗？'
        }) : null
      ])
    }
  }
]

// 选中行
const onChecked = (keys: DataTableRowKey[]) => {
  checkedRowKeys.value = keys
}

// 查看详情
const handleViewDetail = async (row: AlarmItem) => {
  currentAlarm.value = row
  showDetailModal.value = true
  detailLoading.value = true
  analysisData.value = null
  
  try {
    const alarmId = parseInt(row.id) || 0
    if (!alarmId) {
      message.error('无效的告警 ID')
      detailLoading.value = false
      return
    }
    
    const response = await alarmApi.getAlarmAnalysis(alarmId)
    if (response.data?.code === 200 && response.data?.data) {
      analysisData.value = response.data.data
    } else {
      message.error(response.data?.message || '获取告警详情失败')
    }
  } catch (error: any) {
    console.error('获取告警详情失败:', error)
    message.error(error.message || '获取告警详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 查看知识库
const viewKnowledge = (url: string) => {
  message.info(`即将跳转至知识库：${url}`)
  // TODO: 实现知识库跳转逻辑
  window.open(url, '_blank')
}

// 批量确认
const handleBatchAcknowledge = () => {
  if (checkedRowKeys.value.length === 0) {
    message.warning('请选择至少一条告警')
    return
  }
  
  // 发送批量确认事件到父组件
  const ids = checkedRowKeys.value.map(id => id as string)
  emit('batch-acknowledge', ids)
}

// 批量解决
const handleBatchResolve = () => {
  if (checkedRowKeys.value.length === 0) {
    message.warning('请选择至少一条告警')
    return
  }
  
  // 发送批量解决事件到父组件
  const ids = checkedRowKeys.value.map(id => id as string)
  emit('batch-resolve', ids)
}

defineExpose({
  onChecked
})
</script>

<style scoped>
.alarm-detail-content {
  max-height: 600px;
  overflow-y: auto;
  padding: 0 12px;
}

.detail-section {
  margin: 16px 0;
  line-height: 1.8;
}

.related-data {
  background-color: var(--n-code-background-color);
  padding: 16px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}
</style>
