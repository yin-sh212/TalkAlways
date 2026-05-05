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
          
          <!-- 时间范围 -->
          <n-space :size="8" align="center">
            <n-radio-group v-model:value="filters.timeRange" @update:value="handleTimeRangeChange">
              <n-radio-button value="today">今日</n-radio-button>
              <n-radio-button value="week">近 7 天</n-radio-button>
              <n-radio-button value="month">近 30 天</n-radio-button>
            </n-radio-group>
            
            <n-divider vertical />
            
            <!-- 自定义日期选择器 -->
            <n-date-picker
              v-model:value="customDateRange"
              type="daterange"
              placement="bottom-end"
              placeholder="选择日期范围"
              style="width: 240px;"
              @update:value="handleCustomDateChange"
            />
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
                <n-space :size="8">
                  <ChartAIAnalysis 
                    :chart-ref="trendChart"
                    chart-title="能耗 - 环境关联趋势"
                    chart-type="line"
                  />
                  <n-tooltip>
                    <template #trigger>
                      <n-icon size="18" :component="InformationCircle" style="cursor: pointer; color: #1890ff;" />
                    </template>
                    同图展示电力/冷量/供热曲线 + 气温次 Y 轴，标注异常点
                  </n-tooltip>
                </n-space>
              </div>
              <n-skeleton v-if="loading" :rows="3" :height="120" />
              <div v-show="!loading" ref="trendChartRef" class="chart-container"></div>
            </n-grid-item>

            <!-- 图表 2：建筑综合评分对比 -->
            <n-grid-item>
              <div class="chart-header">
                <span class="chart-title">建筑综合评分对比</span>
                <n-space :size="8">
                  <ChartAIAnalysis 
                    :chart-ref="compareChart"
                    chart-title="建筑综合评分对比"
                    chart-type="radar"
                  />
                  <n-tooltip>
                    <template #trigger>
                      <n-icon size="18" :component="InformationCircle" style="cursor: pointer; color: #1890ff;" />
                    </template>
                    雷达图展示多建筑在节能性、稳定性、健康度、能效比四个维度的综合表现
                  </n-tooltip>
                </n-space>
              </div>
              <n-skeleton v-if="loading" :rows="3" :height="120" />
              <div v-show="!loading" ref="compareChartRef" class="chart-container"></div>
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
          <n-skeleton v-if="loading" :rows="4" :height="60" />
          <template v-else>
            <n-alert 
              v-if="currentAnomaly.type !== '无异常'"
              type="warning" 
              :title="`今日最严重异常：${currentAnomaly.type}`"
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
            
            <!-- 无异常时的友好提示 -->
            <n-alert 
              v-else
              type="success" 
              title="设备运行正常"
              closable
              style="margin-bottom: 16px;"
            >
              <template #default>
                <n-space vertical :size="12">
                  <div>当前未检测到明显能耗异常，设备运行平稳。</div>
                  <div>建议：继续保持当前运行策略，定期巡检设备。</div>
                </n-space>
              </template>
            </n-alert>
          </template>
        </n-card>

        <!-- 模块 3：能耗优化洞察 -->
        <n-card 
          title="能耗优化洞察" 
          :bordered="false"
          header-style="padding: 16px 24px;"
          content-style="padding: 0 24px 24px;"
        >
          <n-skeleton v-if="loading" :rows="5" :height="80" />
          <template v-else>
            <n-list hoverable clickable>
              <template #header>
                <div v-if="insights.length === 0" style="padding: 20px; text-align: center; color: var(--text-color-secondary);">
                  <n-empty description="暂无优化洞察数据" />
                </div>
              </template>
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
          </template>
        </n-card>

      </n-space>
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-bar">
      <n-space justify="space-between">
        <n-button 
          type="info" 
          ghost
          @click="navigateToKnowledgeBase"
        >
          <template #icon>
            <n-icon :component="Book" />
          </template>
          前往运维知识库
        </n-button>
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
      </n-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
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
  Alert,
  Book
} from '@vicons/ionicons5'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { getLineChartConfig, getRadarChartConfig, CHART_COLORS } from '@/utils/echarts-config'
import { useBuildingStore } from '@/store/building'
import { getTrendData, getComparisonData } from '@/api/charts'
import { detectAnomaly, getSummary } from '@/api/statistics'
import { getAnalysisInsights } from '@/api/analysis'
import { addDocument } from '@/api/admin'
import { useAppStore } from '@/store/app'
import ChartAIAnalysis from '@/components/common/ChartAIAnalysis.vue'

const router = useRouter()
const message = useMessage()
const appStore = useAppStore()
const buildingStore = useBuildingStore()

// 状态
const loading = ref(false)

// 筛选条件
const filters = reactive({
  buildingId: '',
  dimension: 'energy', // energy | device | alarm
  timeRange: 'week', // today | week | month
  isCustomDate: false // 是否使用自定义日期
})

// 自定义日期范围
const customDateRange = ref<[number, number] | null>(null)

// 建筑选项
const buildingOptions = ref<any[]>([])

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

// 加载建筑列表（从 store 获取固定数据）
const loadBuildings = () => {
  loading.value = true
  
  try {
    const buildings: any[] = buildingStore.buildings || []
    
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
    message.error('获取建筑列表失败，请检查后端服务')
    buildingOptions.value = []
  } finally {
    loading.value = false
  }
}

// 处理时间范围变化
const handleTimeRangeChange = () => {
  filters.isCustomDate = false
  customDateRange.value = null
  handleFilterChange()
}

// 处理自定义日期变化
const handleCustomDateChange = (value: [number, number] | null) => {
  if (value) {
    filters.isCustomDate = true
    // 重置快捷选项的视觉状态
    filters.timeRange = '' as any
    handleFilterChange()
  }
}

// 获取时间范围参数
const getTimeRangeParams = () => {
  if (filters.isCustomDate && customDateRange.value) {
    const startDate = new Date(customDateRange.value[0])
    const endDate = new Date(customDateRange.value[1])
    const days = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1
    
    return {
      start_date: formatDate(startDate),
      end_date: formatDate(endDate),
      days,
      isSingleDay: days === 1
    }
  } else {
    const days = filters.timeRange === 'today' ? 1 : filters.timeRange === 'week' ? 7 : 30
    const mockToday = appStore.getMockToday()
    const endDate = new Date(mockToday)
    const startDate = new Date(endDate)
    startDate.setDate(startDate.getDate() - (days - 1))
    
    return {
      start_date: formatDate(startDate),
      end_date: formatDate(endDate),
      days,
      isSingleDay: days === 1
    }
  }
}

// 格式化日期
const formatDate = (date: Date) => {
  return date.toISOString().split('T')[0]
}

// 处理筛选条件变化
const handleFilterChange = async () => {
  await loadAnalysisData()
}

// 加载分析数据
const loadAnalysisData = async () => {
  if (!filters.buildingId) return
  
  loading.value = true
  
  try {
    // 获取时间范围参数
    const timeParams = getTimeRangeParams()
    
    // 获取所有建筑ID用于对比接口
    const allBuildingIds = buildingOptions.value.map(b => b.value)
    
    // 并行加载所有数据源，提高加载速度
    const [trendRes, anomalyRes, insightsRes, comparisonRes] = await Promise.allSettled([
      // 1. 加载趋势数据
      getTrendData({ 
        building_id: filters.buildingId, 
        days: timeParams.days
      }),
      
      // 2. 加载异常检测数据
      detectAnomaly({
        building_id: filters.buildingId,
        start_date: timeParams.start_date,
        end_date: timeParams.end_date,
        threshold: 2.0
      }),
      
      // 3. 加载分析洞察数据
      getAnalysisInsights({
        building_id: filters.buildingId,
        days: timeParams.days,
        end_date: timeParams.end_date
      }),
      
      // 4. 加载对比数据（所有建筑）
      allBuildingIds.length > 0 ? getComparisonData({
        building_ids: allBuildingIds.join(','),
        start_date: timeParams.start_date,
        end_date: timeParams.end_date
      }) : Promise.reject('没有可用的建筑')
    ])
    
    // 处理趋势数据
    if (trendRes.status === 'fulfilled') {
      updateTrendChart(trendRes.value.data.data, timeParams.isSingleDay)
    } else {
      console.error('加载趋势数据失败:', trendRes.reason)
    }
    
    // 处理异常检测数据
    if (anomalyRes.status === 'fulfilled') {
      const data = anomalyRes.value?.data?.data
      if (data?.anomaly_type && data.anomaly_type !== '无异常') {
        currentAnomaly.value = {
          type: data.anomaly_type || '未知异常',
          description: data.description || '未描述',
          factors: data.factors || '未分析',
          impact: data.impact || '未评估',
          suggestion: data.suggestion || '无建议'
        }
      } else {
        currentAnomaly.value = {
          type: '无异常',
          description: '当前未检测到明显能耗异常',
          factors: '设备运行平稳',
          impact: '无额外能耗损失',
          suggestion: '继续保持当前运行策略，定期巡检设备'
        }
      }
    } else {
      console.error('加载异常检测数据失败:', anomalyRes.reason)
    }
    
    // 处理分析洞察数据
    if (insightsRes.status === 'fulfilled') {
      if (insightsRes.value?.data?.data?.insights) {
        insights.value = insightsRes.value.data.data.insights
      } else {
        insights.value = []
        console.warn('[Analysis] 警告：没有有效的洞察数据')
      }
    } else {
      console.error('加载洞察数据失败:', insightsRes.reason)
      insights.value = []
    }
    
    // 处理对比数据
    if (comparisonRes.status === 'fulfilled') {
      if (comparisonRes.value?.data?.data) {
        updateCompareChartWithDimension(comparisonRes.value.data.data)
      }
    } else {
      console.error('加载对比数据失败:', comparisonRes.reason)
    }
    
    message.success('数据加载成功')
    
  } catch (error) {
    console.error('加载分析数据失败:', error)
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 更新趋势图表 - 支持小时/天粒度切换
const updateTrendChart = (data: any, isSingleDay: boolean = false) => {
  if (!trendChartRef.value) {
    console.error('[Analysis] 趋势图表容器不存在')
    return
  }
  
  // 确保在 DOM 渲染完成后执行
  nextTick(() => {
    if (!trendChartRef.value) return
    
    if (!trendChart) {
      trendChart = echarts.init(trendChartRef.value)
    }
    
    const categories = data.categories || []
    const series = data.series || []
    
    // 根据是否为单天设置不同的 X 轴标签
    const xAxisConfig = isSingleDay ? {
      type: 'category' as const,
      name: '时间',
      axisLabel: {
        formatter: '{value}:00',
        rotate: 45
      }
    } : {
      type: 'category' as const,
      name: '日期',
      axisLabel: {
        formatter: (value: string) => {
          // 简化日期显示
          const date = new Date(value)
          return `${date.getMonth() + 1}/${date.getDate()}`
        },
        rotate: 45
      }
    }
    
    const option: EChartsOption = {
      ...getLineChartConfig(categories, series.map((s: any) => ({
        name: s.name,
        data: s.data,
        areaStyle: !!s.areaStyle,
        smooth: true
      })), {
        yAxisName: isSingleDay ? '功率 (kW)' : '能耗 (MWh)',
        tooltipFormatter: isSingleDay 
          ? '{b}:00 - {c} kW' 
          : '{b}: {c} MWh',
        grid: {
          left: '3%',
          right: '3%',
          bottom: '15%',
          containLabel: true,
        }
      }),
      legend: {
        orient: 'horizontal',
        bottom: 10,
        left: 'center',
        itemWidth: 12,
        itemHeight: 12,
        textStyle: {
          fontSize: 12,
        },
        data: series.map((s: any) => s.name),
      },
      xAxis: {
        ...xAxisConfig,
        data: categories
      }
    }
    
    trendChart.setOption(option)
  })
}

// 更新对比图表 - 支持多维度切换和雷达图
const updateCompareChartWithDimension = (data: any) => {
  // 确保在 DOM 渲染完成后执行
  nextTick(() => {
    if (!compareChartRef.value) {
      console.error('[Analysis] 对比图表容器不存在')
      return
    }
    
    if (!compareChart) {
      compareChart = echarts.init(compareChartRef.value)
    }
    
    // 后端直接返回 radar_data，不需要再访问 data.radar_data
    const radarData = data
    
    if (!radarData || !radarData.buildings || radarData.buildings.length === 0) {
      console.error('[Analysis] 警告：没有有效的雷达图数据')
      return
    }
    
    // 固定使用雷达图模式 - 每个建筑一个多边形，多个指标作为轴
    const seriesData = radarData.buildings.map((b: any, index: number) => {
      return {
        name: b.building_name,
        value: b.values,
        color: CHART_COLORS.palette[index % CHART_COLORS.palette.length]
      }
    })
    
    const option = getRadarChartConfig(radarData.indicators, seriesData, {
      title: '建筑综合评分对比',
      shape: 'circle',
      splitNumber: 5
    })
    
    compareChart.setOption(option)
  })
}


// 保存建议到知识库
const saveSuggestionToKnowledge = async () => {
  try {
    // 将优化建议保存为知识库文档
    const documentData = {
      title: `能耗优化建议 - ${currentAnomaly.value.type}`,
      category: 'optimization',
      tags: ['能耗优化', currentAnomaly.value.type, '运行策略'],
      summary: currentAnomaly.value.suggestion,
      description: currentAnomaly.value.description,
      solution: currentAnomaly.value.suggestion,
      notes: [
        `关联因素：${currentAnomaly.value.factors}`,
        `影响评估：${currentAnomaly.value.impact}`
      ]
    }
    
    const response = await addDocument(documentData)
    
    if (response.data.code === 200) {
      message.success('已成功保存到知识库')
    } else {
      throw new Error(response.data.message || '保存失败')
    }
  } catch (error: any) {
    console.error('[Analysis] 保存建议失败:', error)
    message.error(error.response?.data?.message || '保存失败，请稍后重试')
  }
}

// 复制洞察
const copyInsight = (insight: any) => {
  const text = `${insight.title} - ${insight.description}`
  navigator.clipboard.writeText(text)
  message.success('已复制到剪贴板')
}

// 保存洞察到工作区
const saveInsightToWorkspace = async (insight: any) => {
  try {
    // 将洞察保存为知识库文档
    const documentData = {
      title: insight.title,
      category: insight.category.toLowerCase(),
      tags: [insight.category, insight.type],
      summary: insight.description,
      description: `${insight.title} - ${insight.description}`,
      solution: '基于数据分析得出的优化建议',
      notes: [`颜色标识：${insight.color}`, `类型：${insight.type}`]
    }
    
    // 调用后端知识库 API 保存洞察
    const response = await addDocument(documentData)
    if (response.data.code === 200) {
      message.success('已成功保存到工作区')
    } else {
      throw new Error(response.data.message || '保存失败')
    }
    
  } catch (error: any) {
    console.error('[Analysis] 保存洞察失败:', error)
    message.error(error.response?.data?.message || '保存失败，请稍后重试')
  }
}

// 处理洞察点击
const handleInsightClick = (insight: any) => {
  // 显示洞察详情的 Toast 提示
  message.info(`洞察详情：${insight.title}`, {
    duration: 3000
  })
  
  // 可以在这里实现更详细的弹窗或下钻分析
  console.log('[Analysis] 查看洞察详情:', insight)
}

// 刷新数据
const handleRefresh = async () => {
  message.loading('正在刷新数据...')
  await loadAnalysisData()
  message.success('数据已刷新')
}

// 导出分析报告
const handleExport = async () => {
  if (loading.value) {
    message.warning('数据加载中，请稍后再试')
    return
  }
  
  try {
    message.loading('正在生成分析报告...')
    
    // 获取时间范围参数
    const timeParams = getTimeRangeParams()
    
    // 调用导出 PDF 接口 - 使用动态时间范围
    const exportParams = {
      buildings: [filters.buildingId],
      parameter: 'energy', // 添加必需的 parameter 参数
      startTime: new Date(timeParams.start_date).getTime(),
      endTime: new Date(timeParams.end_date).getTime(),
      format: 'pdf' as const
    }
    
    // 使用 analysis API 中的 exportPDF 函数
    const { exportPDF } = await import('@/api/analysis')
    const response = await exportPDF(exportParams)
    
    // exportPDF 返回的是 AxiosResponse，需要提取 data 中的 Blob
    const blob = response.data

    // 检查是否是有效的 PDF blob
    if (!blob || blob.size === 0) {
      throw new Error('下载的文件为空，请检查后端接口是否正常')
    }
    
    // 检查返回的是否是 PDF（防止后端返回错误 JSON）
    if (blob.type && !blob.type.includes('application/pdf')) {
      // 如果不是 PDF，可能是后端返回了错误信息
      const text = await blob.text()
      try {
        const error = JSON.parse(text)
        throw new Error(error.message || error.error || 'PDF 生成失败')
      } catch {
        throw new Error('后端返回的数据格式不正确')
      }
    }
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `能耗分析报告_${filters.buildingId}_${timeParams.end_date}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    message.success('分析报告下载成功')
  } catch (error: any) {
    message.error(error.response?.data?.message || error.message || '导出失败，请稍后重试')
  }
}

// 跳转到运维知识库
const navigateToKnowledgeBase = () => {
  router.push('/workspace?tab=knowledge')
  message.info('正在跳转到运维知识库...')
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
  
  // 默认选择第一个建筑（如果有）
  if (buildingOptions.value.length > 0 && !filters.buildingId) {
    filters.buildingId = buildingOptions.value[0].value
  }
  
 
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