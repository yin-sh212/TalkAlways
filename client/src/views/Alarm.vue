<template>
  <div class="alarm-container">
    <!-- 顶部查询条件栏 -->
    <div class="query-section">
      <n-card :bordered="false" content-style="padding: 20px;">
        <n-collapse :default-expanded-keys="['query-form']" arrow-placement="right">
          <n-collapse-item title="查询条件" name="query-form">
            <n-form :model="queryForm" :rules="queryRules" ref="queryFormRef" label-placement="top">
              <n-grid :cols="4" :x-gap="16" :y-gap="16">
                <!-- 建筑选择 -->
                <n-grid-item>
                  <n-form-item label="建筑选择" path="buildings">
                    <n-select
                      v-model:value="queryForm.buildings"
                      placeholder="请选择建筑"
                      filterable
                      multiple
                      :options="buildingOptions"
                    />
                  </n-form-item>
                </n-grid-item>

                <!-- 告警级别 -->
                <n-grid-item>
                  <n-form-item label="告警级别" path="severity">
                    <n-select
                      v-model:value="queryForm.severity"
                      placeholder="请选择级别"
                      multiple
                      :options="severityOptions"
                    />
                  </n-form-item>
                </n-grid-item>

                <!-- 告警类型 -->
                <n-grid-item>
                  <n-form-item label="告警类型" path="alarmType">
                    <n-select
                      v-model:value="queryForm.alarmType"
                      placeholder="请选择类型"
                      multiple
                      :options="alarmTypeOptions"
                    />
                  </n-form-item>
                </n-grid-item>

                <!-- 时间范围 -->
                <n-grid-item>
                  <n-form-item label="时间范围" path="timeRange">
                    <n-space :size="8" style="width: 100%;">
                      <n-date-picker
                        v-model:value="queryForm.timeRange"
                        type="daterange"
                        placeholder="选择日期范围"
                        style="flex: 1;"
                      />
                      <n-space :size="4">
                        <n-button size="small" @click="setQuickTime('today')">今日</n-button>
                        <n-button size="small" @click="setQuickTime('week')">本周</n-button>
                        <n-button size="small" @click="setQuickTime('month')">本月</n-button>
                      </n-space>
                    </n-space>
                  </n-form-item>
                </n-grid-item>
              </n-grid>

              <!-- 操作按钮 -->
              <n-space justify="end" style="margin-top: 16px;">
                <n-button @click="handleReset">重置</n-button>
                <n-button type="primary" @click="handleQuery" :loading="queryLoading">
                  查询
                </n-button>
              </n-space>
            </n-form>
          </n-collapse-item>
        </n-collapse>
      </n-card>
    </div>

    <!-- 告警统计指标卡 -->
    <div class="metrics-section">
      <AlarmKpiCards 
        :metrics="metrics"
        :loading="metricsLoading"
      />
    </div>

    <!-- 告警图表分析 -->
    <div class="charts-section">
      <n-grid :cols="24" :x-gap="16" :y-gap="16">
        <n-grid-item :span="16">
          <AlarmTrend 
            ref="alarmTrendRef"
            :trendData="trendData"
            :loading="chartLoading"
          />
        </n-grid-item>
        <n-grid-item :span="8">
          <AlarmDistribution 
            ref="alarmDistributionRef"
            :distributionData="distributionData"
            :loading="chartLoading"
          />
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 告警列表 -->
    <div class="list-section">
      <AlarmList 
        ref="alarmListRef"
        :tableData="tableData"
        :loading="tableLoading"
        :pagination="pagination"
        @update="handleTableUpdate"
        @acknowledge="handleAcknowledge"
        @resolve="handleResolve"
      />
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-bar">
      <n-button type="primary" @click="handleExport" :loading="exportLoading">
        <template #icon>
          <n-icon :component="Download" />
        </template>
        {{ exportLoading ? '生成中...' : '导出报表' }}
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { Download, Alert } from '@vicons/ionicons5'
import AlarmKpiCards from '@/components/alarm/KpiCards.vue'
import AlarmTrend from '@/components/alarm/Trend.vue'
import AlarmDistribution from '@/components/alarm/Distribution.vue'
import AlarmList from '@/components/alarm/List.vue'
import * as analysisApi from '@/api/analysis'
import type { QueryParams } from '@/types/analysis'

const message = useMessage()

// 状态
const queryLoading = ref(false)
const tableLoading = ref(false)
const metricsLoading = ref(false)
const chartLoading = ref(false)
const exportLoading = ref(false)

// 查询表单
const queryFormRef = ref<any>(null)
const queryForm = reactive({
  buildings: [] as string[],
  severity: [] as string[],
  alarmType: [] as string[],
  timeRange: null as [number, number] | null
})

// 验证规则
const queryRules = {
  timeRange: {
    required: true,
    message: '请选择时间范围',
    trigger: 'change'
  }
}

// 建筑选项
const buildingOptions = [
  { label: '行政楼', value: 'building-001' },
  { label: '教学楼 A', value: 'building-002' },
  { label: '教学楼 B', value: 'building-003' },
  { label: '图书馆', value: 'building-004' },
  { label: '实验楼', value: 'building-005' }
]

// 告警级别选项
const severityOptions = [
  { label: '紧急', value: 'critical', style: { color: '#f5222d' } },
  { label: '重要', value: 'major', style: { color: '#fa8c16' } },
  { label: '一般', value: 'minor', style: { color: '#1890ff' } },
  { label: '提示', value: 'warning', style: { color: '#52c41a' } }
]

// 告警类型选项
const alarmTypeOptions = [
  { label: '能耗异常', value: 'energy_anomaly' },
  { label: '设备故障', value: 'device_fault' },
  { label: '传感器异常', value: 'sensor_error' },
  { label: '通信故障', value: 'communication_error' },
  { label: '超限告警', value: 'threshold_exceeded' }
]

// 表格数据
const tableData = ref<any[]>([])
const pagination = reactive({
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
})

// 指标数据
const metrics = ref({
  totalAlarms: 0,
  unresolvedCount: 0,
  criticalCount: 0,
  acknowledgedCount: 0
})

// 图表数据
const trendData = ref<any[]>([])
const distributionData = ref<any[]>([])

// 组件引用
const alarmTrendRef = ref<InstanceType<typeof AlarmTrend> | null>(null)
const alarmDistributionRef = ref<InstanceType<typeof AlarmDistribution> | null>(null)
const alarmListRef = ref<InstanceType<typeof AlarmList> | null>(null)

// 设置快捷时间
const setQuickTime = (type: 'today' | 'week' | 'month') => {
  const now = new Date()
  let start: Date
  let end: Date

  switch (type) {
    case 'today':
      start = new Date(now.setHours(0, 0, 0, 0))
      end = new Date(now.setHours(23, 59, 59, 999))
      break
    case 'week':
      const dayOfWeek = now.getDay()
      start = new Date(now.setDate(now.getDate() - dayOfWeek))
      start.setHours(0, 0, 0, 0)
      end = new Date(now.setDate(now.getDate() + (6 - dayOfWeek)))
      end.setHours(23, 59, 59, 999)
      break
    case 'month':
      start = new Date(now.getFullYear(), now.getMonth(), 1)
      end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999)
      break
  }

  queryForm.timeRange = [start.getTime(), end.getTime()]
}

// 执行查询
const handleQuery = async () => {
  try {
    await queryFormRef.value?.validate()
  } catch (error) {
    message.warning('请填写完整的查询条件')
    return
  }

  queryLoading.value = true
  tableLoading.value = true
  metricsLoading.value = true
  chartLoading.value = true

  try {
    const queryParams: QueryParams = {
      buildings: queryForm.buildings,
      parameter: 'alarm',
      startTime: queryForm.timeRange?.[0] || 0,
      endTime: queryForm.timeRange?.[1] || 0,
      pageSize: pagination.pageSize,
      pageNum: pagination.page
    }

    // 并行调用多个接口
    const [alarmData, statsData] = await Promise.all([
      analysisApi.queryData(queryParams),
      analysisApi.getStatisticsSummary({
        buildings: queryParams.buildings,
        parameter: 'alarm',
        startTime: queryParams.startTime,
        endTime: queryParams.endTime
      })
    ])

    // 填充表格数据
    tableData.value = alarmData.data.data.map((item: any) => ({
      id: item.id,
      time: item.timestamp,
      buildingName: item.building_name || '未知建筑',
      alarmType: item.alarm_type || '未知类型',
      severity: item.severity || 'warning',
      description: item.description || '',
      status: item.status || 'unresolved',
      acknowledgeTime: item.acknowledge_time,
      resolveTime: item.resolve_time
    }))

    // 填充指标数据
    metrics.value = {
      totalAlarms: tableData.value.length,
      unresolvedCount: tableData.value.filter(item => item.status === 'unresolved').length,
      criticalCount: tableData.value.filter(item => item.severity === 'critical').length,
      acknowledgedCount: tableData.value.filter(item => item.status === 'acknowledged').length
    }

    // 准备图表数据
    trendData.value = tableData.value
    distributionData.value = tableData.value

    // 更新图表
    if (alarmTrendRef.value) {
      alarmTrendRef.value.updateChart(trendData.value)
    }
    if (alarmDistributionRef.value) {
      alarmDistributionRef.value.updateChart(distributionData.value)
    }

    message.success('查询成功')
  } catch (error: any) {
    message.error('查询失败：' + error.message)
  } finally {
    queryLoading.value = false
    tableLoading.value = false
    metricsLoading.value = false
    chartLoading.value = false
  }
}

// 重置查询
const handleReset = () => {
  queryForm.buildings = []
  queryForm.severity = []
  queryForm.alarmType = []
  queryForm.timeRange = null
  tableData.value = []
  metrics.value = {
    totalAlarms: 0,
    unresolvedCount: 0,
    criticalCount: 0,
    acknowledgedCount: 0
  }
  trendData.value = []
  distributionData.value = []
  
  if (alarmTrendRef.value) {
    alarmTrendRef.value.clearChart()
  }
  if (alarmDistributionRef.value) {
    alarmDistributionRef.value.clearChart()
  }
  
  message.success('已重置')
}

// 表格更新回调
const handleTableUpdate = (page: number, pageSize: number) => {
  pagination.page = page
  pagination.pageSize = pageSize
  handleQuery()
}

// 确认告警
const handleAcknowledge = async (alarmId: string) => {
  try {
    // TODO: 调用后端确认接口
    message.success('告警已确认')
    handleQuery()
  } catch (error: any) {
    message.error('确认失败：' + error.message)
  }
}

// 解决告警
const handleResolve = async (alarmId: string) => {
  try {
    // TODO: 调用后端解决接口
    message.success('告警已解决')
    handleQuery()
  } catch (error: any) {
    message.error('解决失败：' + error.message)
  }
}

// 导出报表
const handleExport = async () => {
  exportLoading.value = true
  message.info('正在生成报表...')
  
  try {
    const exportParams = {
      buildings: queryForm.buildings,
      parameter: 'alarm',
      startTime: queryForm.timeRange?.[0] || 0,
      endTime: queryForm.timeRange?.[1] || 0,
      format: 'excel' as const
    }

    const response = await analysisApi.exportReport(exportParams)
    
    const url = window.URL.createObjectURL(response.data as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `告警报表_${new Date().toLocaleDateString()}_${Date.now()}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    message.success('报表已下载')
  } catch (error: any) {
    message.error('导出失败：' + error.message)
  } finally {
    exportLoading.value = false
  }
}

onMounted(() => {
  // 初始化时执行一次查询
  handleQuery()
})
</script>

<style scoped>
.alarm-container {
  padding: 16px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.query-section {
  margin-bottom: 16px;
}

.metrics-section {
  margin-bottom: 16px;
}

.charts-section {
  margin-bottom: 16px;
}

.list-section {
  margin-bottom: 16px;
}

.bottom-bar {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}
</style>
