<template>
  <div class="chart-ai-analysis">
    <!-- AI 分析按钮 -->
    <n-tooltip trigger="hover">
      <template #trigger>
        <n-button 
          text 
          type="primary"
          @click="handleAnalyze"
          :loading="analyzing"
          size="small"
        >
          <template #icon>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M5 3a2 2 0 0 0-2 2"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M5 19a2 2 0 0 1-2-2"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>
              <circle cx="12" cy="12" r="3"/><path d="M12 9v2m0 2v.01"/><path d="M19.07 4.93l-2.12 2.12M7.05 16.95l-2.12 2.12M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12"/>
            </svg>
          </template>
        </n-button>
      </template>
      AI 分析此图表
    </n-tooltip>

    <!-- 分析结果弹窗 -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      title="AI 智能分析报告"
      style="width: 800px;"
      :bordered="false"
      :segmented="{ content: 'soft' }"
      @close="handleClose"
    >
      <div v-if="analyzing" class="analysis-loading">
        <n-progress
          type="line"
          status="success"
          :percentage="progress"
          :show-indicator="true"
          :height="8"
        />
        <p class="loading-tip">{{ loadingTip }}</p>
        <n-space vertical align="center" style="margin-top: 16px;">
          <n-text depth="3" style="font-size: 12px;">
            ⏱️ 预计耗时 5-15 秒 | 📊 正在分析 {{ chartDataSummary }}
          </n-text>
        </n-space>
      </div>
      
      <div v-else-if="analysisResult">
        <!-- 关键发现摘要 -->
        <div v-if="keyFindings.length > 0" class="key-findings">
          <n-alert type="info" title="💡 关键发现" :bordered="false">
            <div class="findings-list">
              <div 
                v-for="(finding, index) in keyFindings" 
                :key="index"
                class="finding-item"
              >
                <span class="finding-text">{{ finding }}</span>
              </div>
            </div>
          </n-alert>
        </div>
        
        <!-- 完整分析报告 -->
        <div v-html="renderedMarkdown"></div>
        
        <!-- 操作按钮 -->
        <div class="action-buttons">
          <n-button @click="handleCopy" secondary>
            <template #icon>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </template>
            复制报告
          </n-button>
          <n-button @click="handleExportPDF" secondary>
            <template #icon>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </template>
            导出 PDF
          </n-button>
          <n-button @click="handleSaveToKnowledge" secondary>
            <template #icon>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
            </template>
            保存到知识库
          </n-button>
          <n-button type="primary" @click="handleReAnalyze">
            <template #icon>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
              </svg>
            </template>
            重新分析
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { extractChartData } from '@/utils/chart-data-extractor'
import { analyzeChartWithAIStream } from '@/api/chart-analysis'
import { saveToKnowledge } from '@/api/knowledge'
import type { SSEMessage } from '@/types/chart-analysis'
import { useMessage, useNotification } from 'naive-ui'
import { marked } from 'marked'

// Props: 接收图表实例引用
const props = defineProps<{
  chartRef: HTMLElement | null
  chartTitle: string
  chartType?: string
}>()

const message = useMessage()
const notification = useNotification()
const modalVisible = ref(false)
const analyzing = ref(false)
const progress = ref(0)
const loadingTip = ref('正在初始化...')
const analysisResult = ref<string>('')
const fullText = ref<string>('')
const keyFindings = ref<string[]>([])
const analysisStartTime = ref<number>(0)
let abortController: AbortController | null = null

// 渲染 Markdown
const renderedMarkdown = computed(() => {
  return marked.parse(analysisResult.value) as string
})

// 图表数据摘要
const chartDataSummary = computed(() => {
  if (!props.chartType) return '图表'
  const typeMap: Record<string, string> = {
    line: '折线图',
    bar: '柱状图',
    pie: '饼图',
    radar: '雷达图',
    scatter: '散点图',
    area: '面积图'
  }
  return typeMap[props.chartType] || props.chartType
})

// 处理分析
const handleAnalyze = async () => {
  const chartElement = props.chartRef
  
  if (!chartElement) {
    message.error('图表未初始化')
    return
  }
  
  modalVisible.value = true
  analyzing.value = true
  analysisResult.value = ''
  fullText.value = ''
  keyFindings.value = []
  progress.value = 0
  loadingTip.value = '正在提取图表数据...'
  analysisStartTime.value = Date.now()
  
  try {
    await nextTick()
    
    // 1. 提取图表数据
    loadingTip.value = '正在提取图表数据...'
    progress.value = 10
    
    const chartData = extractChartData(chartElement, {
      title: props.chartTitle,
      type: props.chartType
    })
    
    console.log('[Chart AI] 提取的图表数据:', chartData)
    progress.value = 20
    loadingTip.value = '正在调用 AI 分析服务...'
    
    // 2. 调用后端流式 API
    abortController = new AbortController()
    
    const controller = analyzeChartWithAIStream(chartData, (msg: SSEMessage) => {
      if (msg.type === 'result') {
        const content = msg.data.content || ''
        fullText.value += content
        analysisResult.value = fullText.value
        progress.value = Math.min(90, 20 + Math.floor((fullText.value.length / 100) * 70))
      } else if (msg.type === 'done') {
        const duration = ((Date.now() - analysisStartTime.value) / 1000).toFixed(1)
        analyzing.value = false
        progress.value = 100
        message.success(`分析完成！耗时 ${duration}秒`)
        extractKeyFindings()
      } else if (msg.type === 'error') {
        analyzing.value = false
        message.error(msg.data.message || '分析失败')
      } else if (msg.type === 'status') {
        loadingTip.value = msg.data.message || '分析中...'
        console.log('[Chart AI] 分析状态:', msg.data.message)
      }
    }, abortController.signal)
    
    // 存储 controller 以便取消
    ;(window as any).__chartAnalysisController = controller
    
  } catch (error: any) {
    console.error('[Chart AI] 分析失败:', error)
    analyzing.value = false
    const errorMsg = error.name === 'AbortError' 
      ? '分析已取消' 
      : (error.message || '分析失败，请稍后重试')
    message.error(errorMsg)
  }
}

// 提取关键发现（从分析结果中提取前 3-5 条）
const extractKeyFindings = () => {
  const lines = analysisResult.value.split('\n').filter(line => line.trim())
  const findings: string[] = []
  
  // 尝试提取包含关键词的句子
  const keywords = ['发现', '显示', '表明', '增长', '下降', '异常', '峰值', '趋势']
  
  for (const line of lines) {
    if (findings.length >= 5) break
    if (line.length < 50 && line.length > 10) {
      if (keywords.some(kw => line.includes(kw))) {
        findings.push(line.replace(/[#*`]/g, '').trim())
      }
    }
  }
  
  // 如果提取不到，使用前几行
  if (findings.length === 0) {
    findings.push(...lines.slice(0, 3).map(line => line.replace(/[#*`]/g, '').trim()))
  }
  
  keyFindings.value = findings
}

// 复制到剪贴板
const handleCopy = () => {
  if (analysisResult.value) {
    navigator.clipboard.writeText(analysisResult.value)
    message.success('已复制到剪贴板')
  }
}

// 导出为 PDF
const handleExportPDF = async () => {
  if (!analysisResult.value) {
    message.warning('没有可导出的内容')
    return
  }
  
  try {
    // 动态导入 html2pdf.js
    const html2pdf = (await import('html2pdf.js')).default
    
    // 创建临时容器
    const exportContent = document.createElement('div')
    exportContent.style.padding = '20px'
    exportContent.style.backgroundColor = '#fff'
    exportContent.style.color = '#333'
    exportContent.style.width = '210mm' // A4 宽度
    
    // 添加标题
    const title = document.createElement('h1')
    title.textContent = `${props.chartTitle} - AI 分析报告`
    title.style.fontSize = '24px'
    title.style.marginBottom = '20px'
    title.style.color = '#18a058'
    
    // 添加时间戳
    const timestamp = document.createElement('p')
    timestamp.textContent = `生成时间：${new Date().toLocaleString('zh-CN')}`
    timestamp.style.fontSize = '12px'
    timestamp.style.color = '#666'
    timestamp.style.marginBottom = '20px'
    
    // 复制关键发现
    if (keyFindings.value.length > 0) {
      const findingsDiv = document.createElement('div')
      findingsDiv.style.marginBottom = '20px'
      findingsDiv.style.padding = '12px'
      findingsDiv.style.backgroundColor = '#f0faff'
      findingsDiv.style.borderRadius = '6px'
      
      const findingsTitle = document.createElement('h3')
      findingsTitle.textContent = '💡 关键发现'
      findingsTitle.style.fontSize = '16px'
      findingsTitle.style.marginBottom = '10px'
      findingsTitle.style.color = '#1890ff'
      
      findingsDiv.appendChild(findingsTitle)
      
      keyFindings.value.forEach(finding => {
        const findingItem = document.createElement('div')
        findingItem.style.marginBottom = '8px'
        findingItem.style.paddingLeft = '20px'
        findingItem.style.position = 'relative'
        findingItem.innerHTML = `<span style="position:absolute;left:0;top:0;color:#1890ff;">●</span><span>${finding}</span>`
        findingsDiv.appendChild(findingItem)
      })
      
      exportContent.appendChild(findingsDiv)
    }
    
    // 复制 Markdown 渲染后的内容
    const markdownContainer = document.createElement('div')
    markdownContainer.className = 'markdown-body'
    markdownContainer.innerHTML = renderedMarkdown.value
    
    // 应用基础样式
    markdownContainer.style.lineHeight = '1.6'
    markdownContainer.style.fontSize = '14px'
    
    exportContent.appendChild(title)
    exportContent.appendChild(timestamp)
    exportContent.appendChild(markdownContainer)
    document.body.appendChild(exportContent)
    
    const opt = {
      margin: [15, 15, 15, 15],
      filename: `${props.chartTitle.replace(/[\/\\:*?"<>|]/g, '_')}_AI 分析报告_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { 
        scale: 2,
        useCORS: true,
        letterRendering: true,
        allowTaint: false,
        logging: false
      },
      jsPDF: { 
        unit: 'mm', 
        format: 'a4', 
        orientation: 'portrait',
        compress: true
      },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    }
    
    await html2pdf().set(opt).from(exportContent).save()
    
    // 清理临时元素
    document.body.removeChild(exportContent)
    
    message.success('PDF 导出成功')
  } catch (error: any) {
    console.error('[Chart AI] PDF 导出失败:', error)
    message.error(`PDF 导出失败：${error.message || '请稍后重试'}`)
  }
}

// 保存到知识库
const handleSaveToKnowledge = async () => {
  if (!analysisResult.value) {
    message.warning('没有可保存的内容')
    return
  }
  
  try {
    message.loading('正在保存...', { duration: 1000 })
    
    // 准备知识库文档数据
    const documentData = {
      title: `${props.chartTitle} - AI 分析报告`,
      category: 'chart_analysis',
      tags: [props.chartType || 'chart', 'ai_analysis'],
      summary: keyFindings.value.slice(0, 2).join('。'),
      description: `图表类型：${chartDataSummary.value}\n\n分析结果：`,
      solution: analysisResult.value,
      notes: [`生成时间：${new Date().toLocaleString('zh-CN')}`]
    }
    
    // 调用 API 保存
    const result = await saveToKnowledge(documentData)
    
    if (result.success) {
      message.success(`✅ 已保存到知识库（文档 ID: ${result.documentId}）`)
      
      // 显示通知
      notification.success({
        title: '保存成功',
        content: `分析报告已保存到知识库，文档 ID: ${result.documentId}`,
        duration: 3000
      })
    } else {
      throw new Error('保存失败')
    }
  } catch (error: any) {
    console.error('[Chart AI] 保存失败:', error)
    message.error(`保存失败：${error.message || '请稍后重试'}`)
  }
}

// 重新分析
const handleReAnalyze = () => {
  handleAnalyze()
}

// 关闭弹窗
const handleClose = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  analyzing.value = false
}

// 监听 props 变化
watch(() => props.chartRef, (newVal) => {
  if (!newVal && modalVisible.value) {
    modalVisible.value = false
    message.warning('图表实例已失效')
  }
}, { immediate: true })
</script>

<style scoped>
.chart-ai-analysis {
  display: inline-block;
}

.analysis-loading {
  padding: 40px 20px;
  text-align: center;
}

.loading-tip {
  margin-top: 16px;
  color: #666;
  font-size: 13px;
  font-weight: 500;
}

.key-findings {
  margin-bottom: 16px;
}

.key-findings .findings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.key-findings .finding-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(16, 108, 255, 0.05);
  border-radius: 6px;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.key-findings .finding-dot {
  color: #106cff;
  font-size: 12px;
  line-height: 1.5;
  flex-shrink: 0;
}

.key-findings .finding-text {
  flex: 1;
  font-size: 13px;
  line-height: 1.5;
  color: var(--n-text-color);
  word-wrap: break-word;
  overflow-wrap: break-word;
  min-width: 0;
}

.markdown-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 8px;
  background: #fafafa;
  border-radius: 8px;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-content :deep(*) {
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .n-button {
    width: 100%;
  }
}

/* PDF 导出专用样式 */
.pdf-export-content {
  position: absolute;
  left: -9999px;
  top: 0;
  width: 210mm; /* A4 宽度 */
}

.pdf-export-content h1,
.pdf-export-content h2,
.pdf-export-content h3 {
  page-break-after: avoid;
}

.pdf-export-content img {
  page-break-inside: avoid;
}
</style>
