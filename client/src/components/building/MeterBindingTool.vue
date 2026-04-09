<template>
  <div class="meter-binding-tool">
    <n-card title="监测点绑定工具" size="small">
      <!-- 当前空间信息 -->
      <n-alert v-if="space" type="info" style="margin-bottom: 16px">
        当前空间：{{ space.name }} ({{ space.code }})
      </n-alert>

      <!-- 已绑定列表 -->
      <n-divider title-placement="left">已绑定监测点</n-divider>
      <n-data-table
        :columns="boundColumns"
        :data="boundMeters"
        :pagination="false"
        size="small"
        style="margin-bottom: 16px"
      >
        <template #empty>
          <n-empty description="暂无绑定监测点" />
        </template>
      </n-data-table>

      <!-- 可绑定列表 -->
      <n-divider title-placement="left">可绑定监测点</n-divider>
      <n-spin :show="loadingUnbound">
        <n-data-table
          :columns="unboundColumns"
          :data="unboundMeters"
          :pagination="{ pageSize: 5 }"
          size="small"
          :row-key="(row: any) => row.id"
          @update:checked-row-keys="handleCheckChange"
        >
          <template #empty>
            <n-empty description="没有可绑定的监测点" />
          </template>
        </n-data-table>
      </n-spin>

      <!-- 操作按钮 -->
      <n-space style="margin-top: 16px" justify="end">
        <n-button 
          type="primary" 
          :disabled="selectedMeterIds.length === 0"
          @click="handleBatchBind"
        >
          批量绑定 ({{ selectedMeterIds.length }})
        </n-button>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, h } from 'vue'
import { useMessage, NButton } from 'naive-ui'
import type { Space } from '@/types/building'

interface Props {
  space: Space | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'binding-updated'): void
}>()

const message = useMessage()

// 状态管理
const boundMeters = ref<any[]>([])
const unboundMeters = ref<any[]>([])
const loadingUnbound = ref(false)
const selectedMeterIds = ref<string[]>([])

// 已绑定表格列
const boundColumns = [
  { title: '监测点ID', key: 'id', width: 120 },
  { title: '类型', key: 'type', width: 80 },
  { title: '状态', key: 'status', width: 80 },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (row: any) => h(
      NButton,
      {
        size: 'small',
        type: 'error',
        text: true,
        onClick: () => handleUnbind(row.id)
      },
      { default: () => '解绑' }
    )
  }
]

// 可绑定表格列
const unboundColumns = [
  { 
    type: 'selection' as const,
    disabled: (row: any) => !props.space
  },
  { title: '监测点ID', key: 'id', width: 120 },
  { title: '建筑', key: 'building_id', width: 150 },
  { title: '类型', key: 'type', width: 80 },
  { title: '状态', key: 'status', width: 80 }
]

// 加载已绑定监测点
const loadBoundMeters = async () => {
  if (!props.space) return
  
  try {
    const response = await fetch(`/api/meter-binding/bound-list?space_id=${props.space.id}`)
    const result = await response.json()
    
    if (result.code === 200) {
      boundMeters.value = result.data
    }
  } catch (error) {
    console.error('加载已绑定监测点失败:', error)
  }
}

// 加载未绑定监测点
const loadUnboundMeters = async () => {
  if (!props.space) return
  
  loadingUnbound.value = true
  try {
    // 获取同楼层的未绑定监测点
    const response = await fetch(`/api/meter-binding/unbound?floor_id=${props.space.floor_id}`)
    const result = await response.json()
    
    if (result.code === 200) {
      unboundMeters.value = result.data
    }
  } catch (error) {
    console.error('加载未绑定监测点失败:', error)
    message.error('加载可绑定监测点失败')
  } finally {
    loadingUnbound.value = false
  }
}

// 复选框变化
const handleCheckChange = (keys: any[]) => {
  selectedMeterIds.value = keys as string[]
}

// 批量绑定
const handleBatchBind = async () => {
  if (!props.space || selectedMeterIds.value.length === 0) return
  
  try {
    const bindList = selectedMeterIds.value.map(meterId => ({
      meter_id: meterId,
      space_id: props.space!.id
    }))
    
    const response = await fetch('/api/meter-binding/batch-bind', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bindList)
    })
    
    const result = await response.json()
    
    if (result.code === 200) {
      message.success(result.message)
      selectedMeterIds.value = []
      await refreshData()
      emit('binding-updated')
    } else {
      message.error(result.message || '绑定失败')
    }
  } catch (error) {
    console.error('批量绑定失败:', error)
    message.error('网络错误，请重试')
  }
}

// 解绑
const handleUnbind = async (meterId: string) => {
  try {
    const response = await fetch('/api/meter-binding/unbind', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meter_id: meterId })
    })
    
    const result = await response.json()
    
    if (result.code === 200) {
      message.success('解绑成功')
      await refreshData()
      emit('binding-updated')
    } else {
      message.error(result.message || '解绑失败')
    }
  } catch (error) {
    console.error('解绑失败:', error)
    message.error('网络错误，请重试')
  }
}

// 刷新数据
const refreshData = async () => {
  await Promise.all([loadBoundMeters(), loadUnboundMeters()])
}

// 监听 space 变化
watch(() => props.space, (newSpace) => {
  if (newSpace) {
    selectedMeterIds.value = []
    refreshData()
  }
}, { immediate: true })
</script>

<style scoped>
.meter-binding-tool {
  padding: 16px;
}
</style>
