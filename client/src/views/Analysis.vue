<template>
  <div class="analysis-container">
    <!-- 顶部轻量筛选栏 -->
    <div class="filter-section">
      <n-card :bordered="false" content-style="padding: 16px 24px;">
        <n-space :size="24" align="center">
          <!-- 建筑选择 -->
          <n-select
            v-model:value="filters.buildingId"
            placeholder="选择建筑"
            :options="buildingOptions"
            style="width: 200px;"
            @update:value="handleFilterChange"
          />
          
          <!-- 分析维度 -->
          <n-select
            v-model:value="filters.dimension"
            placeholder="分析维度"
            :options="dimensionOptions"
            style="width: 150px;"
            @update:value="handleFilterChange"
          />
          
          <!-- 时间范围 -->
          <n-space :size="8">
            <n-radio-group v-model:value="filters.timeRange" @update:value="handleFilterChange">
              <n-radio-button value="today">今日</n-radio-button>
              <n-radio-button value="week">近 7 天</n-radio-button>
              <n-radio-button value="month">近 30 天</n-radio-button>
            </n-radio-group>
          </n-space>
        </n-space>
      </n-card>
    </div>

    <!-- 主内容区 -->
    <div class="content-section">
      <n-space vertical :size="16">
        
        <!-- 模块 1：多维度趋势分析 -->
        <n-card title="多维度趋势分析" :bordered="false">
          <n-grid :cols="2" :x-gap="16" :y-gap="16">
            <!-- 图表 1：能耗 - 环境关联趋势图 -->
            <n-grid-item>
              <div class="chart-header">
                <span class="chart-title">能耗 - 环境关联趋势</span>
                <n-tooltip>
                  <template #trigger>
                    <n-icon size="18" :component="InformationCircle" style="cursor: pointer; color: #1890ff;" />
                  </template>
                  同图展示电力/冷量/供热曲线 + 气温次 Y 轴，标注异常点
                </n-tooltip>
              </div>
              <div ref="trendChartRef" class="chart-container"></div>
            </n-grid-item>

            <!-- 图表 2：能耗对比分析 -->
            <n-grid-item>
              <div class="chart-header">
                <span class="chart-title">能耗对比分析</span>
                <n-tooltip>
                  <template #trigger>
                    <n-icon size="18" :component="InformationCircle" style="cursor: pointer; color: #1890ff;" />
                  </template>
                  同类型建筑能耗对比，自动标注差异
                </n-tooltip>
              </div>
              <div ref="compareChartRef" class="chart-container"></div>
            </n-grid-item>
          </n-grid>
        </n-card>

        <!-- 模块 2：异常根因智能分析 -->
        <n-card 
          title="异常根因智能分析" 
          :bordered="false"
          header-style="padding: 16px 24px;"
          content-style="padding: 0 24px 24px;"
        >
          <n-alert 
            type="warning" 
            :title="`今日最严重异常：${currentAnomaly.type || '电力突增'}`"
            closable
            style="margin-bottom: 16px;"
          >
            <template #default>
              <n-space vertical :size="12">
                <div><strong>异常表现：</strong>{{ currentAnomaly.description }}</div>
                <div><strong>关联因素：</strong>{{ currentAnomaly.factors }}</div>
                <div><strong>影响评估：</strong>{{ currentAnomaly.impact }}</div>
                <div>
                  <strong>优化建议：</strong>{{ currentAnomaly.suggestion }}
                  <n-button 
                    text 
                    type="primary" 
                    size="small"
                    style="margin-left: 8px;"
                    @click="saveSuggestionToKnowledge"
                  >
                    保存到知识库
                  </n-button>
                </div>
              </n-space>
            </template>
          </n-alert>
        </n-card>

        <!-- 模块 3：能耗优化洞察 -->
        <n-card 
          title="能耗优化洞察" 
          :bordered="false"
          header-style="padding: 16px 24px;"
          content-style="padding: 0 24px 24px;"
        >
          <n-list hoverable clickable>
            <n-list-item 
              v-for="(insight, index) in insights" 
              :key="index"
              @click="handleInsightClick(insight)"
            >
              <template #prefix>
                <n-icon size="20" :color="insight.color" :component="Bulb" />
              </template>
              <n-thing :description="insight.description">
                <template #header>
                  <n-space :size="8" align="center">
                    <span>{{ insight.title }}</span>
                    <n-tag :type="insight.type" size="small">{{ insight.category }}</n-tag>
                  </n-space>
                </template>
                <template #action>
                  <n-space :size="8">
                    <n-button text size="small" @click.stop="copyInsight(insight)">
                      <template #icon>
                        <n-icon :component="Copy" />
                      </template>
                      复制
                    </n-button>
                    <n-button text size="small" @click.stop="saveInsightToWorkspace(insight)">
                      <template #icon>
                        <n-icon :component="Save" />
                      </template>
                      保存
                    </n-button>
                  </n-space>
                </template>
              </n-thing>
            </n-list-item>
          </n-list>
        </n-card>

      </n-space>
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-bar">
      <n-space justify="end">
        <n-button @click="handleRefresh">
          <template #icon>
            <n-icon :component="Refresh" />
          </template>
          刷新
        </n-button>
        <n-button type="primary" @click="handleExport">
          <template #icon>
            <n-icon :component="Download" />
          </template>
          导出分析报告
        </n-button>
      </n-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { 
  InformationCircle,
  Bulb,
  Copy,
  Save,
  Download,
  Refresh,
  TrendingUp,
  Flash,
  Thermometer,
  Water,
  Alert
} from '@vicons/ionicons5'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { getLineChartConfig, getBarChartConfig } from '@/utils/echarts-config'
import { getBuildings } from '@/api/query'
import { getTrendData, getDistributionData, getComparisonData } from '@/api/charts'
import { detectAnomaly, getSummary } from '@/api/statistics'
import { getAnalysisInsights } from '@/api/analysis'
import { MOCK_TODAY } from '@/api/dashboard'

const message = useMessage()

// 筛选条件
const filters = reactive({
  buildingId: '',
  dimension: 'energy', // energy | device | alarm
  timeRange: 'week' // today | week | month
})

// 建筑选项
const buildingOptions = ref<any[]>([])

// 分析维度选项
const dimensionOptions = [
  { label: '能耗分析', value: 'energy' },
  { label: '设备分析', value: 'device' },
  { label: '告警分析', value: 'alarm' }
]

// 当前异常数据
const currentAnomaly = ref({
  type: '无异常',
  description: '当前未检测到明显能耗异常',
  factors: '设备运行平稳',
  impact: '无额外能耗损失',
  suggestion: '继续保持当前运行策略，定期巡检设备'
})

// 优化洞察数据 - 初始为空，由 API 加载
const insights = ref<any[]>([])

// 图表实例
let trendChart: echarts.ECharts | null = null
let compareChart: echarts.ECharts | null = null
const trendChartRef = ref<HTMLElement | null>(null)
const compareChartRef = ref<HTMLElement | null>(null)

// 加载建筑列表
const loadBuildings = async () => {
  try {
    const response = await getBuildings()
    const buildings: any[] = response.data.data || []
    
    buildingOptions.value = buildings.map((building: any) => ({
      label: building.name || `建筑${building.id}`,
      value: building.id
    }))
    
    // 默认选中第一个建筑
    if (buildings.length > 0) {
      filters.buildingId = buildings[0].id || buildings[0]
      handleFilterChange()
    }
  } catch (error) {
    console.error('获取建筑列表失败:', error)
    // 使用 Mock 数据
    buildingOptions.value = [
      { label: '行政楼', value: 'B001' },
      { label: '教学楼 A', value: 'B002' },
      { label: '教学楼 B', value: 'B003' }
    ]
    filters.buildingId = 'B001'
    handleFilterChange()
  }
}

// 处理筛选条件变化
const handleFilterChange = async () => {
  await loadAnalysisData()
}

// 加载分析数据
const loadAnalysisData = async () => {
  if (!filters.buildingId) return
  
  try {
    // 串行加载多个数据源，避免一个失败导致全部失败
    const days = filters.timeRange === 'today' ? 1 : filters.timeRange === 'week' ? 7 : 30
    
    // 1. 加载趋势数据
    let trendRes: any = null
    try {
      trendRes = await getTrendData({ 
        building_id: filters.buildingId, 
        days: days,
        end_date: MOCK_TODAY
      })
      updateTrendChart(trendRes.data.data)
    } catch (error) {
      console.error('加载趋势数据失败:', error)
    }
    
    // 2. 加载异常检测数据
    let anomalyRes: any = null
    try {
      anomalyRes = await detectAnomaly({
        building_id: filters.buildingId,
        start_date: MOCK_TODAY,
        end_date: MOCK_TODAY,
        threshold: 2.0
      })
    } catch (error) {
      console.error('加载异常检测数据失败:', error)
    }
    
    // 3. 加载分析洞察数据
    let insightsRes: any = null
    try {
      console.log('请求洞察数据，参数:', {
        building_id: filters.buildingId,
        days: days,
        end_date: MOCK_TODAY
      })
      insightsRes = await getAnalysisInsights({
        building_id: filters.buildingId,
        days: days,
        end_date: MOCK_TODAY
      })
      console.log('洞察数据响应:', insightsRes)
      
      // 兼容两种响应格式
      const responseData = insightsRes.data.code !== undefined 
        ? insightsRes.data.data  // 标准格式：{code, message, data}
        : insightsRes.data        // 非标准格式：直接返回业务数据
      
      // 更新异常数据 - 使用真实数据
      if (responseData?.anomaly) {
        currentAnomaly.value = responseData.anomaly
      } else if (anomalyRes?.data.data?.anomalies && anomalyRes.data.data.anomalies.length > 0) {
        // detectAnomaly 返回的结构：data.data.anomalies
        currentAnomaly.value = {
          type: '电力突增',
          description: `检测到 ${anomalyRes.data.data.anomaly_count || anomalyRes.data.data.anomalies.length} 个异常点`,
          factors: '基于历史数据标记',
          impact: `异常点数：${anomalyRes.data.data.anomaly_count || anomalyRes.data.data.anomalies.length}`,
          suggestion: '建议检查设备运行状态，优化运行策略'
        }
      }

      // 更新洞察列表 - 使用真实数据
      if (responseData?.insights && responseData.insights.length > 0) {
        insights.value = responseData.insights
      } else {
        // 默认洞察
        insights.value = [
          {
            title: '暂无足够数据生成洞察',
            description: '请确保所选时间段内有完整的能耗数据',
            category: '系统提示',
            type: 'info',
            color: '#1890ff'
          }
        ]
      }
    } catch (error: any) {
      console.error('加载分析洞察数据失败:', error)
      console.error('错误详情:', error.response?.data || error.message)
      // 使用默认洞察
      insights.value = [
        {
          title: '暂无足够数据生成洞察',
          description: '请确保所选时间段内有完整的能耗数据',
          category: '系统提示',
          type: 'info',
          color: '#1890ff'
        }
      ]
    }

    // 4. 加载对比数据
    await loadComparisonData()
    
    message.success('数据加载成功')
    
  } catch (error) {
    console.error('加载分析数据失败:', error)
    message.error('加载数据失败')
  }
}

// 加载对比数据
const loadComparisonData = async () => {
  try {
    const response = await getComparisonData({
      building_ids: [filters.buildingId],
      start_date: MOCK_TODAY,
      end_date: MOCK_TODAY
    })
    
    updateCompareChart(response.data.data)
  } catch (error) {
    console.error('加载对比数据失败:', error)
    // 使用 Mock 数据作为降级方案
    updateCompareChartWithMock()
  }
}

// 使用 Mock 数据更新对比图表
const updateCompareChartWithMock = () => {
  if (!compareChartRef.value) return
  
  if (!compareChart) {
    compareChart = echarts.init(compareChartRef.value)
  }
  
  const mockData = {
    categories: ['行政楼', '教学楼 A', '教学楼 B', '图书馆', '实验楼'],
    series: [{
      name: '总能耗',
      data: [120, 132, 101, 134, 90]
    }]
  }
  
  const option: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const point = params[0]
        return `<div style="font-weight: bold;">${point.name}</div>
                <div>${point.marker} 能耗：${point.value} MWh</div>`
      }
    },
    xAxis: {
      type: 'category',
      data: mockData.categories
    },
    yAxis: {
      type: 'value',
      name: '能耗 (MWh)'
    },
    series: [{
      name: mockData.series[0].name,
      type: 'bar',
      data: mockData.series[0].data,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#83bff6' },
          { offset: 1, color: '#188df0' }
        ])
      }
    }]
  }
  
  compareChart.setOption(option)
}

// 更新趋势图表
const updateTrendChart = (data: any) => {
  if (!trendChartRef.value) return
  
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  
  const categories = data.categories || []
  const series = data.series || []
  
  const option: EChartsOption = {
    ...getLineChartConfig(categories, series.map((s: any) => ({
      name: s.name,
      data: s.data,
      areaStyle: !!s.areaStyle,
      smooth: true
    })), {
      yAxisName: '能耗 (MWh)',
      tooltipFormatter: '{b}: {c} MWh'
    }),
    legend: {
      data: series.map((s: any) => s.name),
      bottom: 10
    }
  }
  
  trendChart.setOption(option)
}

// 更新对比图表
const updateCompareChart = (data: any) => {
  if (!compareChartRef.value) return
  
  if (!compareChart) {
    compareChart = echarts.init(compareChartRef.value)
  }
  
  const categories = data.categories || []
  const series = data.series || []
  
  const option: EChartsOption = {
    ...getBarChartConfig(categories, series.map((s: any) => ({
      name: s.name,
      data: s.data
    })), {
      yAxisName: '能耗 (MWh)'
    }),
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const point = params[0]
        return `<div style="font-weight: bold;">${point.name}</div>
                <div>${point.marker} 能耗：${point.value} MWh</div>`
      }
    }
  }
  
  compareChart.setOption(option)
}

// 保存建议到知识库
const saveSuggestionToKnowledge = () => {
  message.success('已保存到知识库')
  // TODO: 调用知识库 API
}

// 复制洞察
const copyInsight = (insight: any) => {
  const text = `${insight.title} - ${insight.description}`
  navigator.clipboard.writeText(text)
  message.success('已复制到剪贴板')
}

// 保存洞察到工作区
const saveInsightToWorkspace = (insight: any) => {
  message.success('已保存到工作区')
  // TODO: 调用工作区 API
}

// 处理洞察点击
const handleInsightClick = (insight: any) => {
  message.info(`查看洞察详情：${insight.title}`)
  // TODO: 显示详情弹窗或下钻分析
}

// 刷新数据
const handleRefresh = async () => {
  message.loading('正在刷新数据...')
  await loadAnalysisData()
  message.success('数据已刷新')
}

// 导出分析报告
const handleExport = () => {
  message.success('正在生成分析报告...')
  // TODO: 调用导出接口
}

// 初始化图表
const initCharts = () => {
  nextTick(() => {
    if (trendChartRef.value && !trendChart) {
      trendChart = echarts.init(trendChartRef.value)
    }
    if (compareChartRef.value && !compareChart) {
      compareChart = echarts.init(compareChartRef.value)
    }
  })
}

onMounted(async () => {
  await loadBuildings()
  initCharts()
  
  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    trendChart?.resize()
    compareChart?.resize()
  })
})

onUnmounted(() => {
  trendChart?.dispose()
  compareChart?.dispose()
})
</script>

<style scoped lang="scss">
.analysis-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-color);
}

.filter-section {
  padding: 16px 24px;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
}

.content-section {
  flex: 1;
  padding: 24px;
  overflow: auto;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 0 4px;
  
  .chart-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.chart-container {
  width: 100%;
  height: 350px;
}

.bottom-bar {
  padding: 16px 24px;
  background: var(--card-bg);
  border-top: 1px solid var(--border-color);
}
</style>
