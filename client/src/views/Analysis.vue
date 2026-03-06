<template>
  <div class="analysis-container">
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

                <!-- 参数选择 -->
                <n-grid-item>
                  <n-form-item label="参数类型" path="parameter">
                    <n-select
                      v-model:value="queryForm.parameter"
                      placeholder="请选择参数"
                      :options="parameterOptions"
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

                <!-- 自然语言输入 -->
                <n-grid-item>
                  <n-form-item label="自然语言查询" path="naturalQuery">
                    <n-input
                      v-model:value="queryForm.naturalQuery"
                      placeholder="试试说：A 栋上周每天的空调电耗"
                      @keydown.enter="handleNaturalQuery"
                    >
                      <template #prefix>
                        <n-icon :component="Search" />
                      </template>
                    </n-input>
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

    <!-- 结果展示区 -->
    <div class="result-section">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- Tab 1: 数据表格 -->
        <n-tab-pane name="table" tab="数据表格">
          <n-card :bordered="false" content-style="padding: 16px;">
            <n-data-table
              :columns="tableColumns"
              :data="tableData"
              :loading="tableLoading"
              :pagination="pagination"
              :row-key="(row) => row.id"
              striped
            />
          </n-card>
        </n-tab-pane>

        <!-- Tab 2: 分析视图 -->
        <n-tab-pane name="analysis" tab="分析视图">
          <n-grid :cols="24" :x-gap="16" :y-gap="16">
            <!-- 左侧图表区 -->
            <n-grid-item :span="16">
              <n-card :bordered="false" content-style="padding: 16px;">
                <n-space vertical :size="16">
                  <!-- 图表 1：能耗趋势 -->
                  <div class="chart-wrapper">
                    <div class="chart-header">
                      <span class="chart-title">能耗趋势折线图</span>
                      <n-icon 
                        size="20" 
                        style="cursor: pointer;" 
                        :component="Expand"
                        @click="showChartDetail(0)"
                      />
                    </div>
                    <div ref="chart1Ref" class="chart-container"></div>
                  </div>

                  <!-- 图表 2：能耗分布 -->
                  <div class="chart-wrapper">
                    <div class="chart-header">
                      <span class="chart-title">能耗分布柱状图</span>
                      <n-icon 
                        size="20" 
                        style="cursor: pointer;" 
                        :component="Expand"
                        @click="showChartDetail(1)"
                      />
                    </div>
                    <div ref="chart2Ref" class="chart-container"></div>
                  </div>
                </n-space>
              </n-card>
            </n-grid-item>

            <!-- 右侧指标卡 -->
            <n-grid-item :span="8">
              <n-space vertical :size="16">
                <n-card :bordered="false" content-style="padding: 20px;">
                  <template #header>
                    <n-space justify="space-between">
                      <span class="metric-title">查询时段总能耗</span>
                      <n-icon size="24" color="#1890ff">
                        <Energy />
                      </n-icon>
                    </n-space>
                  </template>
                  <div class="metric-value">{{ metrics.totalEnergy.toFixed(2) }} MWh</div>
                </n-card>

                <n-card :bordered="false" content-style="padding: 20px;">
                  <template #header>
                    <n-space justify="space-between">
                      <span class="metric-title">平均能耗</span>
                      <n-icon size="24" color="#52c41a">
                        <TrendingUp />
                      </n-icon>
                    </n-space>
                  </template>
                  <div class="metric-value">{{ metrics.avgEnergy.toFixed(2) }} MWh</div>
                </n-card>

                <n-card :bordered="false" content-style="padding: 20px;">
                  <template #header>
                    <n-space justify="space-between">
                      <span class="metric-title">异常点数</span>
                      <n-icon size="24" color="#f5222d">
                        <Alert />
                      </n-icon>
                    </n-space>
                  </template>
                  <div class="metric-value" style="color: #f5222d;">{{ metrics.anomalyCount }}</div>
                </n-card>
              </n-space>
            </n-grid-item>
          </n-grid>
        </n-tab-pane>
      </n-tabs>
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

    <!-- 图表详情弹窗 -->
    <n-modal
      v-model:show="showChartModal"
      preset="card"
      title="图表详情"
      style="width: 90%; max-width: 1200px;"
    >
      <div ref="detailChartRef" class="detail-chart-container"></div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { 
  Search, 
  Expand, 
  Download, 
  Alert, 
  TrendingUp, 
  Flash as Energy 
} from '@vicons/ionicons5'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import type { DataTableColumns } from 'naive-ui'

const message = useMessage()

// 状态
const queryLoading = ref(false)
const tableLoading = ref(false)
const exportLoading = ref(false)
const activeTab = ref<'table' | 'analysis'>('table')
const showChartModal = ref(false)

// 图表实例
let chart1: echarts.ECharts | null = null
let chart2: echarts.ECharts | null = null
let detailChart: echarts.ECharts | null = null
const chart1Ref = ref<HTMLElement | null>(null)
const chart2Ref = ref<HTMLElement | null>(null)
const detailChartRef = ref<HTMLElement | null>(null)

// 查询表单
const queryFormRef = ref<any>(null)
const queryForm = reactive({
  buildings: [] as string[],
  parameter: 'electricity',
  timeRange: null as [number, number] | null,
  naturalQuery: ''
})

// 验证规则
const queryRules = {
  buildings: {
    required: true,
    message: '请选择建筑',
    trigger: 'change'
  },
  timeRange: {
    required: true,
    message: '请选择时间范围',
    trigger: 'change'
  }
}

// 建筑选项（Mock 数据）
const buildingOptions = [
  { label: '行政楼', value: 'building-001' },
  { label: '教学楼 A', value: 'building-002' },
  { label: '教学楼 B', value: 'building-003' },
  { label: '图书馆', value: 'building-004' },
  { label: '实验楼', value: 'building-005' }
]

// 参数选项
const parameterOptions = [
  { label: '电力能耗', value: 'electricity' },
  { label: '空调能耗', value: 'hvac' },
  { label: '环境温度', value: 'temperature' },
  { label: 'COP 值', value: 'cop' }
]

// 表格数据
const tableData = ref<any[]>([])
const tableColumns: DataTableColumns = [
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
    title: '参数类型',
    key: 'parameterName',
    width: 120
  },
  {
    title: '数值',
    key: 'value',
    width: 120,
    sorter: 'default'
  },
  {
    title: '单位',
    key: 'unit',
    width: 100
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) => {
      if (row.isAnomaly) {
        return h(
          'span',
          { style: { color: '#f5222d', fontWeight: 'bold' } },
          '异常'
        )
      }
      return h('span', '正常')
    }
  }
]

// 表格分页
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
  totalEnergy: 0,
  avgEnergy: 0,
  anomalyCount: 0
})

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

// 自然语言查询
const handleNaturalQuery = async () => {
  if (!queryForm.naturalQuery.trim()) {
    message.warning('请输入查询内容')
    return
  }

  queryLoading.value = true
  try {
    // TODO: 调用 NL2Query 解析接口
    // const parsedResult = await parseNaturalQuery(queryForm.naturalQuery)
    
    // Mock 解析结果
    const mockParsedResult = {
      buildings: ['building-001'],
      parameter: 'hvac',
      timeRange: [Date.now() - 7 * 24 * 3600 * 1000, Date.now()]
    }

    // 回填到表单
    queryForm.buildings = mockParsedResult.buildings
    queryForm.parameter = mockParsedResult.parameter
    queryForm.timeRange = mockParsedResult.timeRange as [number, number]

    message.success('解析成功，已自动填充查询条件')
    
    // 执行查询
    await handleQuery()
  } catch (error: any) {
    message.error('解析失败：' + error.message)
  } finally {
    queryLoading.value = false
  }
}

// 执行查询
const handleQuery = async () => {
  // 验证表单
  try {
    await queryFormRef.value?.validate()
  } catch (error) {
    message.warning('请填写完整的查询条件')
    return
  }

  tableLoading.value = true
  queryLoading.value = true

  try {
    // TODO: 调用数据查询接口
    // const result = await queryData(queryForm)
    
    // Mock 数据
    const mockData = generateMockData()
    tableData.value = mockData.tableData
    metrics.value = mockData.metrics

    // 更新图表
    updateCharts(mockData)

    message.success('查询成功')
    
    // 切换到表格 Tab
    activeTab.value = 'table'
  } catch (error: any) {
    message.error('查询失败：' + error.message)
  } finally {
    tableLoading.value = false
    queryLoading.value = false
  }
}

// 重置查询
const handleReset = () => {
  queryForm.buildings = []
  queryForm.parameter = 'electricity'
  queryForm.timeRange = null
  queryForm.naturalQuery = ''
  tableData.value = []
  metrics.value = {
    totalEnergy: 0,
    avgEnergy: 0,
    anomalyCount: 0
  }
  
  // 清空图表
  chart1?.clear()
  chart2?.clear()
  
  message.success('已重置')
}

// 导出报表
const handleExport = async () => {
  exportLoading.value = true
  message.info('正在生成报表...')
  
  try {
    // TODO: 调用导出接口
    // await exportReport(queryForm)
    
    // Mock 导出
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    message.success('报表已下载')
  } catch (error: any) {
    message.error('导出失败：' + error.message)
  } finally {
    exportLoading.value = false
  }
}

// 显示图表详情
const showChartDetail = (index: number) => {
  showChartModal.value = true
  
  setTimeout(() => {
    if (detailChartRef.value) {
      detailChart = echarts.init(detailChartRef.value)
      const option = index === 0 ? getChart1Option() : getChart2Option()
      detailChart?.setOption(option)
    }
  }, 100)
}

// 更新图表
const updateCharts = (data: any) => {
  // 图表 1：能耗趋势
  if (chart1Ref.value) {
    chart1 = echarts.init(chart1Ref.value)
    chart1.setOption(getChart1Option())
  }

  // 图表 2：能耗分布
  if (chart2Ref.value) {
    chart2 = echarts.init(chart2Ref.value)
    chart2.setOption(getChart2Option())
  }
}

// 获取图表 1 配置（折线图）
const getChart1Option = (): EChartsOption => {
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const point = params[0]
        let html = `<div>${point.name}</div>`
        params.forEach((p: any) => {
          const color = p.data.isAnomaly ? '#f5222d' : '#1890ff'
          html += `<div style="color: ${color}">
            ${p.marker} ${p.seriesName}: ${p.value}
            ${p.data.isAnomaly ? ' <span style="color: #f5222d; font-weight: bold;">(异常点)</span>' : ''}
          </div>`
        })
        return html
      }
    },
    legend: {
      data: ['能耗值']
    },
    xAxis: {
      type: 'category',
      data: ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06', '2024-01-07']
    },
    yAxis: {
      type: 'value',
      name: '能耗 (MWh)'
    },
    series: [
      {
        name: '能耗值',
        type: 'line',
        smooth: true,
        data: [150.5, 180.3, 220.8, 190.6, 175.2, 165.9, 155.8],
        markPoint: {
          data: [
            { 
              type: 'max', 
              name: '最大值',
              itemStyle: { color: '#f5222d' }
            }
          ]
        },
        markLine: {
          data: [
            {
              type: 'average',
              name: '平均值'
            }
          ]
        },
        itemStyle: {
          color: '#1890ff'
        }
      }
    ]
  }
}

// 获取图表 2 配置（柱状图）
const getChart2Option = (): EChartsOption => {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['各建筑能耗']
    },
    xAxis: {
      type: 'category',
      data: ['行政楼', '教学楼 A', '教学楼 B', '图书馆', '实验楼']
    },
    yAxis: {
      type: 'value',
      name: '能耗 (MWh)'
    },
    series: [
      {
        name: '各建筑能耗',
        type: 'bar',
        data: [350.5, 280.3, 245.8, 195.2, 185.0],
        itemStyle: {
          color: '#1890ff'
        }
      }
    ]
  }
}

// 生成 Mock 数据
const generateMockData = () => {
  const tableData: any[] = []
  const dates = ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06', '2024-01-07']
  const buildings = ['行政楼', '教学楼 A', '教学楼 B', '图书馆', '实验楼']
  
  let totalEnergy = 0
  let anomalyCount = 0

  dates.forEach((date, index) => {
    buildings.forEach((building, buildingIndex) => {
      const value = Math.random() * 50 + 20
      const isAnomaly = Math.random() < 0.1 // 10% 概率异常
      
      if (isAnomaly) anomalyCount++
      totalEnergy += value

      tableData.push({
        id: `${index}-${buildingIndex}`,
        time: date,
        buildingName: building,
        parameterName: '电力能耗',
        value: value.toFixed(2),
        unit: 'MWh',
        isAnomaly
      })
    })
  })

  return {
    tableData,
    metrics: {
      totalEnergy: totalEnergy,
      avgEnergy: totalEnergy / tableData.length,
      anomalyCount
    }
  }
}

// 窗口大小变化时重新渲染图表
const handleResize = () => {
  chart1?.resize()
  chart2?.resize()
  detailChart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart1?.dispose()
  chart2?.dispose()
  detailChart?.dispose()
})
</script>

<style scoped lang="scss">
.analysis-container {
  width: 100%;
  height: 100%;
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

.query-section {
  margin-bottom: 16px;
}

.result-section {
  flex: 1;
  overflow: auto;
}

.chart-wrapper {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 16px;
  background: #fff;

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .chart-title {
      font-size: 16px;
      font-weight: 500;
      color: #333;
    }
  }

  .chart-container {
    height: 300px;
    width: 100%;
  }
}

.metric-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

  .metric-title {
    font-size: 14px;
    color: #666;
    font-weight: 500;
  }

  .metric-value {
    font-size: 28px;
    font-weight: bold;
    color: #333;
    margin-top: 12px;
  }
}

.bottom-bar {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
}

.detail-chart-container {
  height: 600px;
  width: 100%;
}

:deep(.n-card) {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

:deep(.n-data-table) {
  font-size: 14px;
}
</style>
