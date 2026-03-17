<template>
  <n-card title="能耗详情" :bordered="false" content-style="padding: 16px;">
    <template #header-extra>
      <n-space>
        <n-button size="small" type="primary" @click="handleExport">
          导出数据
        </n-button>
        <n-button size="small" @click="handleRefresh">
          刷新
        </n-button>
      </n-space>
    </template>
    
    <!-- 汇总信息卡片 -->
    <div v-if="summaryData" class="summary-cards">
      <n-grid :cols="4" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-statistic label="总电量 (kWh)">
            <n-number-animation :from="0" :to="summaryData.total_elec" :precision="2" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="平均电量 (kWh)">
            <n-number-animation :from="0" :to="summaryData.avg_elec" :precision="2" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="总冷量 (kWh)">
            <n-number-animation :from="0" :to="summaryData.total_cooling" :precision="2" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="平均温度 (°C)">
            <n-number-animation :from="0" :to="summaryData.avg_temp" :precision="2" />
          </n-statistic>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 详情数据表格 -->
    <n-data-table
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      :row-key="(row) => row.period"
      striped
      size="small"
    />
  </n-card>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { NButton, NTag, NNumberAnimation, NStatistic } from 'naive-ui'
import type { BuildingEnergyDetail, EnergySummary } from '@/types/analysis'

const message = useMessage()

interface Props {
  tableData: BuildingEnergyDetail[]
  summaryData?: EnergySummary
  loading?: boolean
  buildingId?: string
  period?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  buildingId: '',
  period: ''
})

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'export'): void
}>()

// 分页配置
const pagination = {
  page: 1,
  pageSize: 10,
  pageSizes: [10, 20, 50],
  showSizePicker: true,
  onChange: (page: number) => {
    pagination.page = page
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize
    pagination.page = 1
  }
}

// 格式化数值，添加千分位和精度控制
const formatNumber = (value: number, precision: number = 2) => {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision
  })
}

// 表格列定义
const columns: DataTableColumns = [
  {
    title: '日期',
    key: 'period',
    width: 120,
    fixed: 'left',
    sorter: 'default'
  },
  {
    title: '数据点数',
    key: 'data_points',
    width: 90,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', String(row.data_points))
  },
  {
    title: '总电量 (kWh)',
    key: 'total_elec',
    width: 120,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.total_elec - b.total_elec,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.total_elec))
  },
  {
    title: '平均电量 (kWh)',
    key: 'avg_elec',
    width: 120,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.avg_elec - b.avg_elec,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.avg_elec))
  },
  {
    title: '最大电量 (kWh)',
    key: 'max_elec',
    width: 120,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.max_elec - b.max_elec,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.max_elec))
  },
  {
    title: '最小电量 (kWh)',
    key: 'min_elec',
    width: 120,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.min_elec - b.min_elec,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.min_elec))
  },
  {
    title: '标准差',
    key: 'std_elec',
    width: 100,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.std_elec, 3))
  },
  {
    title: '总冷量 (kWh)',
    key: 'total_cooling',
    width: 130,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.total_cooling - b.total_cooling,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.total_cooling, 0))
  },
  {
    title: '平均冷量 (kWh)',
    key: 'avg_cooling',
    width: 130,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.avg_cooling, 0))
  },
  {
    title: '最大冷量 (kWh)',
    key: 'max_cooling',
    width: 130,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.max_cooling, 0))
  },
  {
    title: '最小冷量 (kWh)',
    key: 'min_cooling',
    width: 130,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.min_cooling, 0))
  },
  {
    title: '总热量 (kWh)',
    key: 'total_heating',
    width: 130,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.total_heating, 0))
  },
  {
    title: '平均热量 (kWh)',
    key: 'avg_heating',
    width: 130,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.avg_heating, 0))
  },
  {
    title: '最高温 (°C)',
    key: 'max_temp',
    width: 100,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.max_temp - b.max_temp,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.max_temp, 1))
  },
  {
    title: '最低温 (°C)',
    key: 'min_temp',
    width: 100,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.min_temp - b.min_temp,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.min_temp, 1))
  },
  {
    title: '平均温 (°C)',
    key: 'avg_temp',
    width: 100,
    align: 'right',
    sorter: (a: BuildingEnergyDetail, b: BuildingEnergyDetail) => a.avg_temp - b.avg_temp,
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.avg_temp, 1))
  },
  {
    title: '平均压力 (hPa)',
    key: 'avg_pressure',
    width: 120,
    align: 'right',
    render: (row: BuildingEnergyDetail) => h('span', formatNumber(row.avg_pressure, 2))
  }
]

// 刷新数据
const handleRefresh = () => {
  emit('refresh')
  message.success('数据已刷新')
}

// 导出数据
const handleExport = () => {
  emit('export')
  message.success('开始导出数据...')
}

// 暴露方法给父组件
defineExpose({
  handleRefresh,
  handleExport
})
</script>

<style scoped>
.summary-cards {
  margin-bottom: 24px;
  padding: 16px;
  background-color: var(--n-card-color);
  border-radius: 8px;
}

:deep(.n-statistic__label) {
  font-size: 14px;
  color: var(--n-text-color-3);
}

:deep(.n-statistic__value) {
  font-size: 20px;
  font-weight: 600;
  color: var(--n-text-color-1);
}
</style>
