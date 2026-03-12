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
import * as alarmApi from '@/api/alarm'
import type { AlarmItem, AlarmQueryParams } from '@/api/alarm'

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
  timeRange: [
    {
      required: true,
      message: '请选择时间范围',
      trigger: ['blur', 'change'],
      validator: (rule: any, value: [number, number] | null) => {
        if (!value || !Array.isArray(value) || value.length !== 2) {
          return new Error('请选择时间范围')
        }
        if (!value[0] || !value[1]) {
          return new Error('请选择时间范围')
        }
        return true
      }
    }
  ]
}

// 建筑选项（从后端获取）
const buildingOptions = ref<any[]>([])

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

// 获取建筑列表
const loadBuildings = async () => {
  try {
    const response = await alarmApi.getBuildings()
    const buildings = response.data.data || []
    
    buildingOptions.value = buildings.map((building: any) => ({
      label: building.name || `建筑${building.id || building.building_id}`,
      value: building.id || building.building_id
    }))
  } catch (error: any) {
    console.error('获取建筑列表失败:', error)
    // 使用默认 Mock 数据
    buildingOptions.value = [
      { label: '行政楼', value: 'building-001' },
      { label: '教学楼 A', value: 'building-002' },
      { label: '教学楼 B', value: 'building-003' },
      { label: '图书馆', value: 'building-004' },
      { label: '实验楼', value: 'building-005' }
    ]
  }
}

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

// 执行查询 - 对接真实接口
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
    // 准备查询参数
    const startDate = queryForm.timeRange ? new Date(queryForm.timeRange[0]).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
    const endDate = queryForm.timeRange ? new Date(queryForm.timeRange[1]).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
    const buildingId = queryForm.buildings[0] || 'B001'
    
    // 并行调用多个接口
    const [alarmRes, summaryRes, trendRes, distributionRes] = await Promise.all([
      alarmApi.queryAlarms({ // 告警查询
        building_ids: queryForm.buildings.length > 0 ? queryForm.buildings : [buildingId],
        start_date: startDate,
        end_date: endDate,
        severity: queryForm.severity.length > 0 ? queryForm.severity : undefined,
        alarm_type: queryForm.alarmType.length > 0 ? queryForm.alarmType : undefined,
        page: pagination.page,
        page_size: pagination.pageSize
      }),
      alarmApi.getAlarmSummary({ // 统计摘要
        building_id: buildingId,
        start_date: startDate,
        end_date: endDate,
        time_unit: 'day'
      }),
      alarmApi.getAlarmTrend({ // 趋势图数据
        building_id: buildingId,
        start_date: startDate,
        end_date: endDate
      }),
      alarmApi.getAlarmDistribution({ // 分布图数据
        building_id: buildingId,
        date: endDate
      })
    ])

    console.log('告警查询响应:', alarmRes)
    console.log('统计摘要响应:', summaryRes)
    console.log('趋势图响应:', trendRes)
    console.log('分布图响应:', distributionRes)

    // 填充表格数据 - 后端返回的是数组格式
    const alarms = Array.isArray(alarmRes.data.data) ? alarmRes.data.data : []
    
    tableData.value = alarms.map((item: any, index: number) => ({
      id: item.id || item.alarm_id || `alarm_${index}`,
      timestamp: item.timestamp || item.time,
      building_id: item.building_id,
      building_name: item.building_name,
      alarm_type: item.alarm_type,
      severity: item.severity,
      status: item.status || 'unresolved',
      description: item.description,
      buildingName: item.building_name || '未知建筑',
      alarmTypeName: getAlarmTypeName(item.alarm_type),
      severityName: getSeverityName(item.severity)
    }))

    // 填充指标数据 - 使用确切路径 data.data.summary
    const summaryData = summaryRes.data.data?.summary || {}
    metrics.value = {
      totalAlarms: summaryData?.total_alarm_count || alarms.length,
      unresolvedCount: summaryData?.unresolved_count || alarms.filter(a => a.status === 'unresolved').length,
      criticalCount: summaryData?.critical_count || alarms.filter(a => a.severity === 'critical').length,
      acknowledgedCount: summaryData?.acknowledged_count || alarms.filter(a => a.status === 'acknowledged').length
    }

    // 图表数据 - 后端返回的是 { categories, series } 格式
    trendData.value = trendRes.data.data || { categories: [], series: [] }
    distributionData.value = distributionRes.data.data || { categories: [], series: [] }

    console.log('趋势图数据:', trendData.value)
    console.log('分布图数据:', distributionData.value)

    // 更新图表
    if (alarmTrendRef.value) {
      alarmTrendRef.value.updateChart(trendData.value)
    }
    if (alarmDistributionRef.value) {
      alarmDistributionRef.value.updateChart(distributionData.value)
    }

    message.success('查询成功')
  } catch (error: any) {
    console.error('查询失败:', error)
    message.error('查询失败：' + (error.message || '未知错误'))
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

// 获取告警类型名称
const getAlarmTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    'energy_anomaly': '能耗异常',
    'device_fault': '设备故障',
    'sensor_error': '传感器异常',
    'communication_error': '通信故障',
    'threshold_exceeded': '超限告警'
  }
  return typeMap[type] || type
}

// 获取级别名称
const getSeverityName = (severity: string) => {
  const severityMap: Record<string, string> = {
    'critical': '紧急',
    'major': '重要',
    'minor': '一般',
    'warning': '提示'
  }
  return severityMap[severity] || severity
}

// 确认告警 - 对接真实接口
const handleAcknowledge = async (alarmId: string) => {
  try {
    await alarmApi.acknowledgeAlarm({
      alarm_id: alarmId,
      operator: 'current_user' // 实际应从用户信息中获取
    })
    message.success('告警已确认')
    handleQuery() // 刷新列表
  } catch (error: any) {
    console.error('确认失败:', error)
    message.error('确认失败：' + (error.message || '未知错误'))
  }
}

// 解决告警 - 对接真实接口
const handleResolve = async (alarmId: string) => {
  try {
    await alarmApi.resolveAlarm({
      alarm_id: alarmId,
      operator: 'current_user',
      resolution: '已处理'
    })
    message.success('告警已解决')
    handleQuery() // 刷新列表
  } catch (error: any) {
    console.error('解决失败:', error)
    message.error('解决失败：' + (error.message || '未知错误'))
  }
}

// 导出报表 - 对接真实接口
const handleExport = async () => {
  exportLoading.value = true
  message.info('正在生成报表...')
  
  try {
    const startDate = queryForm.timeRange ? new Date(queryForm.timeRange[0]).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
    const endDate = queryForm.timeRange ? new Date(queryForm.timeRange[1]).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
    
    const exportParams = {
      building_ids: queryForm.buildings.length > 0 ? queryForm.buildings : ['B001'],
      startTime: startDate,
      endTime: endDate,
      format: 'excel' as const
    }

    const response = await alarmApi.exportExcel(exportParams)
    
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
    console.error('导出失败:', error)
    message.error('导出失败：' + (error.message || '未知错误'))
  } finally {
    exportLoading.value = false
  }
}

onMounted(() => {
  // 初始化时执行一次查询
  loadBuildings()
  handleQuery()
})
</script>

<style scoped>
.alarm-container {
  padding: 16px;
  background-color:var(--bg-color);
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
