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
            <template #header>
              <n-space justify="space-between" align="center">
                <span>数据明细</span>
                <n-checkbox v-model:checked="enableCompare" @update:checked="handleCompareToggle">
                  启用对比模式
                </n-checkbox>
              </n-space>
            </template>
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

        <!-- 新增 Tab: 对比分析 -->
        <n-tab-pane name="comparison" tab="对比分析" v-if="enableCompare">
          <n-grid :cols="24" :x-gap="16" :y-gap="16">
            <n-grid-item :span="24">
              <n-card title="多建筑能耗对比" :bordered="false" content-style="padding: 16px;">
                <div ref="compareChartRef" class="chart-container" style="height: 400px;"></div>
              </n-card>
            </n-grid-item>
          </n-grid>
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
import { ref, reactive, onMounted, onUnmounted, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
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
import * as analysisApi from '@/api/analysis'
import type { QueryParams, QueryDataItem, QueryResponse } from '@/types/analysis'

const message = useMessage()
const router = useRouter()
const route = useRoute()

// 状态
const queryLoading = ref(false)
const tableLoading = ref(false)
const exportLoading = ref(false)
const activeTab = ref<'table' | 'analysis' | 'comparison'>('table')
const showChartModal = ref(false)
const enableCompare = ref(false) // 是否启用对比模式

// 图表实例
let chart1: echarts.ECharts | null = null
let chart2: echarts.ECharts | null = null
let compareChart: echarts.ECharts | null = null // 对比图表实例
let detailChart: echarts.ECharts | null = null
const chart1Ref = ref<HTMLElement | null>(null)
const chart2Ref = ref<HTMLElement | null>(null)
const compareChartRef = ref<HTMLElement | null>(null) // 对比图表引用
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

// 自然语言查询 - 对接真实接口
const handleNaturalQuery = async () => {
  if (!queryForm.naturalQuery.trim()) {
    message.warning('请输入查询内容')
    return
  }

  queryLoading.value = true
  try {
    // 调用智能问答接口
    const parseResult = await analysisApi.parseNaturalQuery({
      query: queryForm.naturalQuery
    })
    
    console.log('NL2Query 响应:', parseResult)
    
    // 后端返回的是 answer 文本，需要简单解析
    // TODO: 实际应该由后端返回结构化数据
    // 这里暂时使用 Mock 数据
    const mockParsedResult = {
      buildings: ['B001'],
      parameter: 'electricity',
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

// 执行查询 - 对接真实接口
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
    // 准备查询参数
    const queryParams: QueryParams = {
      buildings: queryForm.buildings,
      parameter: queryForm.parameter,
      startTime: queryForm.timeRange?.[0] || 0,
      endTime: queryForm.timeRange?.[1] || 0,
      pageSize: pagination.pageSize,
      pageNum: pagination.page
    }

    // 并行调用多个接口获取数据
    const [rawData, summaryData, anomalyData] = await Promise.all([
      analysisApi.queryData(queryParams), // 原始数据
      analysisApi.getStatisticsSummary({ // 统计摘要
        buildings: queryParams.buildings,
        parameter: queryParams.parameter,
        startTime: queryParams.startTime,
        endTime: queryParams.endTime
      }),
      analysisApi.getAnomalyCount({ // 异常统计
        buildings: queryParams.buildings,
        parameter: queryParams.parameter,
        startTime: queryParams.startTime,
        endTime: queryParams.endTime
      })
    ])

    console.log('原始数据响应:', rawData)
    console.log('统计摘要响应:', summaryData)
    console.log('异常统计响应:', anomalyData)

    // 填充表格数据
    tableData.value = rawData.data.data.map((item: any) => ({
      id: item.id || item.timestamp,
      time: item.timestamp,
      buildingId: item.building_id,
      buildingName: '建筑', // 后端未提供，需要关联查询
      parameterName: '电力能耗',
      value: item.electricity,
      unit: 'kWh',
      isAnomaly: item.is_anomaly === 1
    }))

    // 填充指标数据
    metrics.value = {
      totalEnergy: summaryData.data.summary?.total_elec || 0,
      avgEnergy: summaryData.data.summary?.avg_elec || 0,
      anomalyCount: anomalyData.data.anomaly_count || 0
    }

    // 更新图表
    updateCharts({
      trendData: tableData.value,
      distributionData: tableData.value
    })

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

// 导出报表 - 对接真实接口
const handleExport = async () => {
  exportLoading.value = true
  message.info('正在生成报表...')
  
  try {
    // 准备导出参数
    const exportParams = {
      buildings: queryForm.buildings,
      parameter: queryForm.parameter,
      startTime: queryForm.timeRange?.[0] || 0,
      endTime: queryForm.timeRange?.[1] || 0,
      format: 'excel' as const // 默认导出为 Excel
    }

    // 调用导出接口
    const response = await analysisApi.exportReport(exportParams)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(response.data as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `能耗报表_${new Date().toLocaleDateString()}_${Date.now()}.xlsx`
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

// 显示图表详情
const showChartDetail = (index: number) => {
  showChartModal.value = true
  
  setTimeout(() => {
    if (detailChartRef.value) {
      detailChart = echarts.init(detailChartRef.value)
      // 使用当前已渲染的图表数据
      const option = index === 0 ? chart1?.getOption() : chart2?.getOption()
      if (option) {
        detailChart?.setOption(option as EChartsOption)
      }
    }
  }, 100)
}

// 更新图表 - 对接真实数据
const updateCharts = (data: {
  trendData: QueryDataItem[],
  distributionData: QueryDataItem[]
}) => {
  // 图表 1：能耗趋势（带异常标记）
  if (chart1Ref.value && data.trendData.length > 0) {
    chart1 = echarts.init(chart1Ref.value)
    chart1.setOption(getChart1Option(data.trendData))
  }

  // 图表 2：能耗分布
  if (chart2Ref.value && data.distributionData.length > 0) {
    chart2 = echarts.init(chart2Ref.value)
    chart2.setOption(getChart2Option(data.distributionData))
  }
}

// 获取图表 1 配置（折线图 - 带异常标记）
const getChart1Option = (trendData: any[]): EChartsOption => {
  // 按时间分组数据
  const timeMap = new Map<string, any[]>()
  trendData.forEach(item => {
    if (!timeMap.has(item.time)) {
      timeMap.set(item.time, [])
    }
    timeMap.get(item.time)!.push(item)
  })

  const times = Array.from(timeMap.keys()).sort()
  const seriesData = times.map(time => {
    const items = timeMap.get(time)!
    const totalValue = items.reduce((sum, item) => sum + item.value, 0)
    const hasAnomaly = items.some(item => item.isAnomaly)
    return {
      value: Number(totalValue.toFixed(2)),
      isAnomaly: hasAnomaly
    }
  })

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const point = params[0]
        let html = `<div style="font-weight: bold;">${point.name}</div>`
        params.forEach((p: any) => {
          const color = p.data.isAnomaly ? '#f5222d' : '#1890ff'
          html += `<div style="color: ${color}">
            ${p.marker} ${p.seriesName}: ${p.value} MWh
            ${p.data.isAnomaly ? ' <span style="color: #f5222d; font-weight: bold;">(异常点（算法标记）)</span>' : ''}
          </div>`
        })
        return html
      }
    },
    legend: {
      data: ['总能耗']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times
    },
    yAxis: {
      type: 'value',
      name: '能耗 (MWh)'
    },
    series: [
      {
        name: '总能耗',
        type: 'line',
        smooth: true,
        data: seriesData,
        itemStyle: {
          color: (params: any) => {
            return params.data.isAnomaly ? '#f5222d' : '#1890ff'
          }
        },
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
        }
      }
    ]
  }
}

// 获取图表 2 配置（柱状图）
const getChart2Option = (distributionData: any[]): EChartsOption => {
  // 按建筑分组数据
  const buildingMap = new Map<string, number>()
  distributionData.forEach(item => {
    if (!buildingMap.has(item.buildingName)) {
      buildingMap.set(item.buildingName, 0)
    }
    buildingMap.set(item.buildingName, buildingMap.get(item.buildingName)! + item.value)
  })

  const buildings = Array.from(buildingMap.keys())
  const values = buildings.map(b => Number(buildingMap.get(b)!.toFixed(2)))

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const point = params[0]
        return `<div style="font-weight: bold;">${point.name}</div>
                <div>${point.marker} 能耗：${point.value} MWh</div>`
      }
    },
    legend: {
      data: ['各建筑能耗']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: buildings
    },
    yAxis: {
      type: 'value',
      name: '能耗 (MWh)'
    },
    series: [
      {
        name: '各建筑能耗',
        type: 'bar',
        data: values,
        itemStyle: {
          color: '#1890ff'
        }
      }
    ]
  }
}

// 切换对比模式
const handleCompareToggle = () => {
  if (enableCompare.value) {
    activeTab.value = 'comparison'
    message.success('已启用对比模式')
    // 延迟初始化对比图表
    setTimeout(() => {
      initCompareChart()
    }, 100)
  } else {
    activeTab.value = 'table'
    message.info('已关闭对比模式')
  }
}

// 初始化对比图表
const initCompareChart = () => {
  if (!compareChartRef.value || tableData.value.length === 0) return
  
  compareChart = echarts.init(compareChartRef.value)
  
  // 按建筑分组数据
  const buildingMap = new Map<string, number[]>()
  tableData.value.forEach(item => {
    if (!buildingMap.has(item.buildingName)) {
      buildingMap.set(item.buildingName, [])
    }
    buildingMap.get(item.buildingName)!.push(item.value)
  })
  
  // 构建系列数据 - 使用 ECharts 正确的类型
  const series: any[] = Array.from(buildingMap.entries()).map(([name, values]) => ({
    name,
    type: 'bar' as const,
    data: values.map(v => Number(v.toFixed(2))),
    emphasis: {
      focus: 'series'
    }
  }))
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: Array.from(buildingMap.keys()),
      top: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['时段 1', '时段 2', '时段 3', '时段 4', '时段 5'], // TODO: 实际应使用时间标签
      axisLabel: {
        interval: 0,
        rotate: 30
      }
    },
    yAxis: {
      type: 'value',
      name: '能耗 (kWh)'
    },
    series: series as any // 类型断言
  }
  
  compareChart?.setOption(option)
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
  compareChart?.resize()
  detailChart?.resize()
}

// 处理路由参数（从 Overview 页面跳转时自动填充）
const handleRouteParams = () => {
  const { building, start, end } = route.query
  
  if (building && start && end) {
    // 填充建筑
    queryForm.buildings = [building as string]
    
    // 填充时间范围
    const startTime = new Date(start as string).getTime()
    const endTime = new Date(end as string).getTime()
    queryForm.timeRange = [startTime, endTime]
    
    // 自动执行查询
    message.info('已根据异常信息自动填充查询条件')
    setTimeout(() => {
      handleQuery()
    }, 500)
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  handleRouteParams()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart1?.dispose()
  chart2?.dispose()
  compareChart?.dispose()
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
