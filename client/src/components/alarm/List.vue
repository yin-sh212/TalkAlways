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
      :row-key="(row) => row.id"
      :checked-row-keys="checkedRowKeys"
      @update:checked-row-keys="onChecked"
      striped
    />
  </n-card>
</template>

<script setup lang="ts">
import { ref, h } from 'vue'
import type { DataTableColumns, DataTableRowKey } from 'naive-ui'
import { NButton, NTag, NPopconfirm } from 'naive-ui'

interface AlarmItem {
  id: string
  time: string
  buildingName: string
  alarmType: string
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
}>()

const checkedRowKeys = ref<DataTableRowKey[]>([])

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

// 表格列定义
const columns: DataTableColumns = [
  {
    type: 'selection',
    disabled: (row: AlarmItem) => row.status === 'resolved'
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
    key: 'alarmType',
    width: 150
  },
  {
    title: '级别',
    key: 'severity',
    width: 100,
    render: (row: AlarmItem) => {
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
    render: (row: AlarmItem) => {
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
    width: 200,
    fixed: 'right',
    render: (row: AlarmItem) => {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
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

// 批量确认
const handleBatchAcknowledge = () => {
  if (checkedRowKeys.value.length === 0) {
    return
  }
  
  checkedRowKeys.value.forEach(id => {
    emit('acknowledge', id as string)
  })
  
  checkedRowKeys.value = []
}

// 批量解决
const handleBatchResolve = () => {
  if (checkedRowKeys.value.length === 0) {
    return
  }
  
  checkedRowKeys.value.forEach(id => {
    emit('resolve', id as string)
  })
  
  checkedRowKeys.value = []
}

defineExpose({
  onChecked
})
</script>

<style scoped>
</style>
