<template>
  <teleport to="body">
    <div class="ai-floating-ball-container">
      <!-- 悬浮小球 -->
      <div
        v-if="!isExpanded"
        ref="ballRef"
        class="ai-ball"
        :style="{ left: position.x + 'px', top: position.y + 'px' }"
        @mousedown="startDrag"
        @click="toggleExpand"
        title="点击展开 AI 分析面板"
      >
        <div class="ai-ball-icon">
          <n-icon size="24" color="#fff">
            <Chatbubbles />
          </n-icon>
        </div>
        <div class="ai-ball-text">AI</div>
        <n-badge
          v-if="hasNewInsights"
          dot
          color="#f5222d"
          class="ai-ball-badge"
        />
      </div>

      <!-- AI 分析面板 -->
      <transition name="slide-fade">
        <div v-if="isExpanded" class="ai-panel-overlay" @click="toggleExpand">
          <div class="ai-panel" :style="panelStyle" @click.stop>
            <div class="ai-panel-header">
              <n-space align="center">
                <n-icon size="20" color="#fff">
                  <Chatbubbles />
                </n-icon>
                <span class="panel-title">AI 数据分析师</span>
                <n-tag type="success" size="small" round>在线</n-tag>
              </n-space>
              <n-button text @click="toggleExpand" size="small" title="关闭面板">
                <n-icon size="18"><Close /></n-icon>
              </n-button>
            </div>

            <div class="ai-panel-content">
              <!-- 对话历史 -->
              <div ref="chatHistoryRef" class="chat-history">
                <div
                  v-for="(message, index) in messages"
                  :key="index"
                  class="message-item"
                  :class="message.role"
                >
                  <div class="message-avatar">
                    <n-icon size="20" :color="message.role === 'user' ? '#18a058' : '#1890ff'">
                      <Person v-if="message.role === 'user'" />
                      <Chatbubbles v-else />
                    </n-icon>
                  </div>
                  <div class="message-content">
                    <div class="message-text" v-html="formatMarkdown(message.content)"></div>
                    
                    <!-- 数据卡片 -->
                    <div v-if="message.supportingData && Object.keys(message.supportingData).length > 0" class="data-card">
                      <n-divider dashed>支撑数据</n-divider>
                      <pre>{{ formatJSON(message.supportingData) }}</pre>
                    </div>
                    
                    <!-- 推荐问题 -->
                    <div v-if="message.suggestedQuestions && message.suggestedQuestions.length > 0" class="suggested-questions">
                      <n-button
                        v-for="(q, i) in message.suggestedQuestions"
                        :key="i"
                        text
                        size="small"
                        @click="askQuestion(q)"
                      >
                        {{ q }} →
                      </n-button>
                    </div>
                  </div>
                </div>
                
                <!-- 加载状态 -->
                <div v-if="isThinking" class="message-item ai">
                  <div class="message-content">
                    <n-spin size="small">
                      <template #description>AI 正在分析数据...</template>
                    </n-spin>
                  </div>
                </div>
              </div>

              <!-- 输入框 -->
              <div class="chat-input-area">
                <n-input
                  v-model:value="inputValue"
                  placeholder="问 AI 任何问题，例如：为什么行政楼能耗偏高？"
                  @keydown.enter.prevent="sendMessage()"
                  :disabled="isThinking"
                  clearable
                >
                  <template #suffix>
                    <n-button text @click="sendMessage()" :loading="isThinking">
                      <n-icon size="18"><Send /></n-icon>
                    </n-button>
                  </template>
                </n-input>
                
                <!-- 快捷操作 -->
                <n-space class="quick-actions" :size="8">
                  <n-button
                    size="small"
                    secondary
                    @click="analyzeCurrentPage"
                    :disabled="isThinking"
                  >
                    <n-icon size="14"><Analytics /></n-icon>
                    分析当前页面
                  </n-button>
                  <n-button
                    size="small"
                    secondary
                    @click="getQuickInsights"
                    :disabled="isThinking"
                  >
                    <n-icon size="14"><Flash /></n-icon>
                    获取洞察
                  </n-button>
                </n-space>
              </div>
            </div>
          </div>
        </div>
      </transition>
      
      <!-- 划词选择浮动按钮 -->
      <transition name="fade">
        <div
          v-if="showSelectionButton"
          class="ai-selection-button"
          :style="{
            left: selectionButtonPosition.x + 'px',
            top: selectionButtonPosition.y + 'px'
          }"
        >
          <div class="selection-button-content" @click="analyzeSelectedText">
            <n-icon size="16" color="#fff">
              <Sparkles />
            </n-icon>
            <span>AI 分析</span>
          </div>
          
          <!-- 推荐问题列表 -->
          <div class="suggested-questions-popup">
            <div v-if="loadingSuggestions" class="loading-suggestions">
              <n-spin size="small" />
              <span>AI 正在思考问题...</span>
            </div>
            <div v-else-if="suggestedQuestionsForSelection && suggestedQuestionsForSelection.length > 0">
              <div class="suggestions-title">💡 推荐问题：</div>
              <n-space vertical :size="4">
                <n-button
                  v-for="(q, i) in suggestedQuestionsForSelection"
                  :key="i"
                  text
                  size="small"
                  @click="askQuestion(q)"
                  class="suggestion-btn"
                >
                  {{ q }}
                </n-button>
              </n-space>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Chatbubbles, Person, Close, Send, Analytics, Flash, Sparkles } from '@vicons/ionicons5'
import { analyzeWithAI, generateQuickSuggestions, getQuickInsights as fetchQuickInsights } from '@/api/ai-analyst'
import { useBuildingStore } from '@/store/building'

interface Message {
  role: 'user' | 'ai'
  content: string
  supportingData?: Record<string, any[]>
  suggestedQuestions?: string[]
}

const route = useRoute()
const buildingStore = useBuildingStore()
const ballRef = ref<HTMLElement | null>(null)
const chatHistoryRef = ref<HTMLElement | null>(null)

// 状态
const isExpanded = ref(false)
const isThinking = ref(false)
const inputValue = ref('')
const messages = ref<Message[]>([])
const hasNewInsights = ref(false)

// 悬浮球位置（默认右下角）
const position = ref({ 
  x: typeof window !== 'undefined' ? window.innerWidth - 70 : 330, 
  y: typeof window !== 'undefined' ? window.innerHeight - 150 : 450 
})
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })

// 面板位置 - 固定在屏幕中央，不随小球位置变化
const panelStyle = computed(() => {
  return {
    // 固定居中定位
    left: '50%',
    top: '50%',
    transform: 'translate(-50%, -50%)'
  }
})

// 拖拽逻辑
const startDrag = (e: MouseEvent) => {
  isDragging.value = true
  const rect = ballRef.value?.getBoundingClientRect()
  if (rect) {
    dragOffset.value = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    }
  }
}

const onDrag = (e: MouseEvent) => {
  if (!isDragging.value) return
  position.value = {
    x: e.clientX - dragOffset.value.x,
    y: e.clientY - dragOffset.value.y
  }
}

const endDrag = () => {
  isDragging.value = false
}

// 切换展开/收起
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
  if (isExpanded.value) {
    // 展开时滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
  }
}

// 发送消息
const sendMessage = async (customQuestion?: string) => {
  const question = customQuestion || inputValue.value.trim()
  if (!question || isThinking.value) return
  
  messages.value.push({
    role: 'user',
    content: question
  })
  
  if (!customQuestion) {
    inputValue.value = ''
  }
  
  isThinking.value = true
  
  try {
    // 获取当前页面上下文
    const context = getPageContext()
    
    // 调用 AI 分析接口
    const response = await analyzeWithAI(question, context)
    const responseData = response.data?.data
    
    if (responseData) {
      messages.value.push({
        role: 'ai',
        content: responseData.answer || '未获取到分析结果',
        supportingData: responseData.supporting_data || {},
        suggestedQuestions: responseData.suggested_questions || []
      })
    } else {
      messages.value.push({
        role: 'ai',
        content: '抱歉，未能获取到有效的分析结果'
      })
    }
    
    // 滚动到底部
    await nextTick()
    scrollToBottom()
    
  } catch (error: any) {
    console.error('AI 分析失败:', error)
    messages.value.push({
      role: 'ai',
      content: `抱歉，分析过程中出现错误：${error.message || '请稍后再试'}`
    })
  } finally {
    isThinking.value = false
  }
}

// 问问题（用于推荐问题点击）
const askQuestion = (question: string) => {
  sendMessage(question)
}

// 获取页面上下文
const getPageContext = () => {
  return {
    current_page: String(route.name || ''),
    current_building_id: buildingStore.currentBuildingId,
    current_date: route.query.date,
    selected_metrics: route.query.metrics,
    query_params: route.query
  }
}

// 分析当前页面
const analyzeCurrentPage = async () => {
  const context = getPageContext()
  const defaultQuestion = getDefaultQuestionForPage(String(route.name))
  
  await sendMessage(defaultQuestion)
}

// 根据页面类型生成默认问题
const getDefaultQuestionForPage = (pageName: string): string => {
  const buildingId = buildingStore.currentBuildingId
  
  switch (pageName) {
    case 'Overview':
      return `分析 ${buildingId || '当前建筑'} 的能耗情况和设备运行状态`
    case 'Analysis':
      return `深度分析 ${buildingId || '当前建筑'} 的能耗趋势和异常点`
    case 'Alarm':
      return `分析当前告警分布和处理情况，识别主要风险点`
    case 'DeviceManagement':
      return `分析设备运行状况和维护需求`
    default:
      return `分析当前页面的关键指标和发现的问题`
  }
}

// 获取快速洞察
const getQuickInsights = async () => {
  isThinking.value = true
  
  try {
    const buildingId = buildingStore.currentBuildingId || 'Eagle_education_Cassie'
    const response = await fetchQuickInsights(buildingId)
    const responseData = response.data?.data
    
    if (responseData && responseData.insights && responseData.insights.length > 0) {
      const insightsText = responseData.insights.map((insight: any) => {
        const priorityIcon = insight.priority === 'high' ? '🔴' : insight.priority === 'medium' ? '🟡' : '🟢'
        return `${priorityIcon} **${insight.title}**\n\n${insight.description}\n\n💡 建议：${insight.action}`
      }).join('\n\n---\n\n')
      
      messages.value.push({
        role: 'ai',
        content: `发现 **${responseData.insights.length}** 个重要洞察：\n\n${insightsText}`
      })
    } else {
      messages.value.push({
        role: 'ai',
        content: '✅ 当前运行状况良好，暂未发现异常情况。继续保持！'
      })
    }
    scrollToBottom()
  } catch (error: any) {
    console.error('获取洞察失败:', error)
    messages.value.push({
      role: 'ai',
      content: `获取洞察失败：${error.message || '请稍后再试'}`
    })
  } finally {
    isThinking.value = false
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

// 简单的 Markdown 格式化（支持粗体、列表等）
const formatMarkdown = (text: string) => {
  if (!text) return ''
  
  // 粗体
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  // 列表
  text = text.replace(/^[•\-]\s+(.*)$/gm, '<li>$1</li>')
  // 换行
  text = text.replace(/\n/g, '<br>')
  
  return text
}

// JSON 格式化
const formatJSON = (obj: any) => {
  return JSON.stringify(obj, null, 2)
}

// 监听全局主题变化（可选）
watch(() => isExpanded.value, (newVal) => {
  if (!newVal) {
    // 收起时清理
  }
})

// 划词选择相关
const selectedText = ref('')
const showSelectionButton = ref(false)
const selectionButtonPosition = ref({ x: 0, y: 0 })
const suggestedQuestionsForSelection = ref<string[]>([])
const loadingSuggestions = ref(false)
let selectionTimer: ReturnType<typeof setTimeout> | null = null

// 推荐问题列表（基于当前页面）- 突出快速、即时、碎片化问题
const suggestedQuestions = computed(() => {
  const page = route.path
  
  // 基于页面的推荐问题 - 都是短平快的即时查询
  const pageQuestions: Record<string, string[]> = {
    '/overview': [
      '今日用电多少？',
      '现在有什么异常？',
      '哪个楼耗能最高？',
      '今日电费多少？'
    ],
    '/analysis': [
      '为什么这个时段高？',
      '昨天同期对比如何？',
      '主要耗能的是什么？',
      '有浪费吗？'
    ],
    '/alarm': [
      '还有几个没处理？',
      '最常见的告警？',
      '最严重的告警？',
      '怎么快速处理？'
    ],
    '/report': [
      '本月用了多少？',
      '比上月多还是少？',
      '超标了吗？',
      '能省多少？'
    ]
  }
  
  return pageQuestions[page] || [
    '今日能耗如何？',
    '有什么异常？',
    '有节能建议吗？',
    '数据正常吗？'
  ]
})

// 监听文本选择
const handleTextSelection = () => {
  // 清除之前的定时器
  if (selectionTimer) {
    clearTimeout(selectionTimer)
  }
  
  // 延迟一点显示，避免选择过程中闪烁
  selectionTimer = setTimeout(async () => {
    const selection = window.getSelection()
    const text = selection?.toString().trim() || ''
    
    // 至少选择 5 个字符才显示按钮
    if (text.length < 5) {
      hideSelectionButton()
      return
    }
    
    selectedText.value = text
    
    // 计算按钮位置（选区末尾上方）
    const range = selection?.getRangeAt(0)
    if (range) {
      const rect = range.getBoundingClientRect()
      
      // 计算位置：选区上方，水平居中
      const buttonWidth = 200 // 估算按钮宽度（包含推荐问题）
      const buttonHeight = 150 // 估算按钮高度（包含推荐问题列表）
      
      selectionButtonPosition.value = {
        x: rect.left + (rect.width / 2) - (buttonWidth / 2),
        y: rect.top - buttonHeight - 8 // 8px 间距
      }
      
      // 确保不超出屏幕
      if (selectionButtonPosition.value.y < 10) {
        selectionButtonPosition.value.y = rect.bottom + 8 // 如果上方空间不够，显示在下方
      }
      
      if (selectionButtonPosition.value.x < 10) {
        selectionButtonPosition.value.x = 10
      }
      
      if (selectionButtonPosition.value.x + buttonWidth > window.innerWidth - 10) {
        selectionButtonPosition.value.x = window.innerWidth - buttonWidth - 10
      }
      
      showSelectionButton.value = true
      
      // AI 生成推荐问题
      await generateSuggestionsForSelection()
    }
  }, 300) // 300ms 延迟，等待选择完成
}

// 隐藏选择按钮
const hideSelectionButton = () => {
  showSelectionButton.value = false
  selectedText.value = ''
  suggestedQuestionsForSelection.value = []
  loadingSuggestions.value = false
}

// 分析选中的文本
const analyzeSelectedText = () => {
  if (!selectedText.value) return
  
  // 自动展开面板
  isExpanded.value = true
  
  // 构造问题
  const question = `请分析这段内容："${selectedText.value}"`
  
  // 发送消息
  sendMessage(question)
  
  // 隐藏按钮
  hideSelectionButton()
}

// 为选中的文本生成 AI 推荐问题
const generateSuggestionsForSelection = async () => {
  if (!selectedText.value) return
  
  loadingSuggestions.value = true
  suggestedQuestionsForSelection.value = []
  
  try {
    // 使用新的快速推荐接口
    const context = getPageContext()
    const response = await generateQuickSuggestions(selectedText.value, context)
    
    if (response.data?.data?.suggestions) {
      suggestedQuestionsForSelection.value = response.data.data.suggestions.slice(0, 3)
    } else {
      // 兜底方案
      suggestedQuestionsForSelection.value = [
        '这是什么意思？',
        '这个数据正常吗？',
        '如何优化？'
      ]
    }
  } catch (error: any) {
    console.warn('生成推荐问题失败（使用预设问题）:', error.message)
    // 失败时使用预设问题，不影响用户体验
    suggestedQuestionsForSelection.value = [
      '这是什么意思？',
      '这个数据正常吗？',
      '如何优化？'
    ]
  } finally {
    loadingSuggestions.value = false
  }
}

onMounted(() => {
  console.log('[AIFloatingBall] 组件已挂载')
  
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', endDrag)
  
  // 监听文本选择（在 document 上监听）
  document.addEventListener('mouseup', handleTextSelection)
  
  // 初始化欢迎消息 - 突出"轻量、快速、即时"的定位，与 Chat 界面的"深度交流"区分
  messages.value.push({
    role: 'ai',
    content: `嗨！我是您的 **AI 速查助手** ⚡

**随时问我任何小问题：**
• 🔍 "今日用电多少？" - 快速查询
• 📊 "现在有什么异常？" - 即时检测  
• 💡 "哪个楼耗能最高？" - 数据对比
• ⏱️ "比昨天多了吗？" - 同环比分析

**特点：**
✅ 即问即答 · ✅ 简短直接 · ✅ 随时打断

💬 想深入讨论？去 [AI 对话] 界面吧~

---

**✨ 新功能：划词分析！**
在页面上选中任何文字（数据、告警描述、图表标题等），点击弹出的"AI 分析"按钮，我会立即为你解读！`
  })
  
  // 调试：在控制台打印位置信息
  console.log('[AIFloatingBall] 初始位置:', position.value)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
  
  // 清理事件监听
  document.removeEventListener('mouseup', handleTextSelection)
  
  if (selectionTimer) {
    clearTimeout(selectionTimer)
  }
})
</script>

<style scoped lang="scss">
.ai-floating-ball-container {
  // 容器不设置定位，让 .ai-ball 直接使用 fixed
  pointer-events: none; // 容器不接收鼠标事件
  z-index: 10000; // 确保小球在最上层
  
  .ai-ball {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #18a058 0%, #1890ff 100%);
    box-shadow: 0 4px 12px rgba(24, 160, 88, 0.4), 0 0 0 3px rgba(255, 255, 255, 0.3);
    cursor: grab;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s;
    position: fixed;
    border: 2px solid rgba(255, 255, 255, 0.5);
    pointer-events: auto;
    z-index: 10001; // 小球在遮罩层之上
    
    &:hover {
      transform: scale(1.15);
      box-shadow: 0 6px 16px rgba(24, 160, 88, 0.6), 0 0 0 3px rgba(255, 255, 255, 0.5);
    }
    
    &:active {
      cursor: grabbing;
    }
    
    .ai-ball-icon {
      animation: pulse 2s infinite;
    }
    
    .ai-ball-text {
      position: absolute;
      bottom: -18px;
      font-size: 10px;
      font-weight: bold;
      color: #fff;
      background: rgba(0, 0, 0, 0.6);
      padding: 2px 6px;
      border-radius: 4px;
      white-space: nowrap;
      pointer-events: none;
    }
    
    .ai-ball-badge {
      position: absolute;
      top: -2px;
      right: -2px;
    }
  }
  
  // 遮罩层
  .ai-panel-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.3);
    z-index: 9998;
    display: flex;
    pointer-events: auto;
    backdrop-filter: blur(2px); // 毛玻璃效果
    
    .ai-panel {
      position: fixed;
      width: 420px;
      height: 620px;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      pointer-events: auto;
      z-index: 9999; // 面板在遮罩层之上，但在小球之下
      
      .ai-panel-header {
        padding: 16px;
        background: linear-gradient(135deg, #18a058 0%, #1890ff 100%);
        color: #fff;
        display: flex;
        justify-content: space-between;
        align-items: center;
        
        .panel-title {
          font-weight: 600;
          font-size: 16px;
        }
      }
      
      .ai-panel-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        
        .chat-history {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          background: #f9f9f9;
          
          .message-item {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            
            &.user {
              flex-direction: row-reverse;
              
              .message-content {
                background: #18a058;
                color: #fff;
              }
            }
            
            .message-avatar {
              flex-shrink: 0;
            }
            
            .message-content {
              max-width: 75%;
              padding: 12px;
              border-radius: 12px;
              background: #f5f5f5;
              box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
              
              .message-text {
                font-size: 14px;
                line-height: 1.6;
                
                :deep(strong) {
                  color: #18a058;
                }
              }
              
              .data-card {
                margin-top: 12px;
                padding: 8px;
                background: rgba(0, 0, 0, 0.05);
                border-radius: 6px;
                
                pre {
                  font-size: 11px;
                  max-height: 150px;
                  overflow-y: auto;
                  white-space: pre-wrap;
                  word-wrap: break-word;
                }
              }
              
              .suggested-questions {
                margin-top: 8px;
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                
                button {
                  font-size: 12px;
                }
              }
            }
          }
        }
        
        .chat-input-area {
          padding: 16px;
          border-top: 1px solid #e8e8e8;
          background: #fff;
          
          .quick-actions {
            margin-top: 8px;
          }
        }
      }
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

// 划词选择浮动按钮
.ai-selection-button {
  position: fixed;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border: 2px solid #667eea;
  cursor: pointer;
  z-index: 10002; // 在所有内容之上
  pointer-events: auto;
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: 220px;
  
  .selection-button-content {
    display: flex;
    align-items: center;
    gap: 8px;
    
    span {
      color: #333;
      font-size: 14px;
      font-weight: 600;
    }
  }
  
  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2);
    border-color: #5568d3;
  }
  
  &:active {
    transform: translateY(-1px);
  }
}

// 推荐问题弹窗
.suggested-questions-popup {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  min-width: 240px;
  max-width: 320px;
  border: 1px solid #e9ecef;
  
  .suggestions-title {
    font-size: 13px;
    color: #495057;
    margin-bottom: 10px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .loading-suggestions {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #868e96;
    font-size: 13px;
    padding: 8px 0;
  }
  
  .suggestion-btn {
    display: block;
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    font-size: 13px;
    color: #333;
    background: #fff;
    border-radius: 6px;
    transition: all 0.2s;
    border: 1px solid #dee2e6;
    margin-bottom: 6px;
    line-height: 1.5;
    
    &:hover {
      background: #667eea;
      color: #fff;
      border-color: #667eea;
      transform: translateX(6px);
    }
    
    &:last-child {
      margin-bottom: 0;
    }
  }
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

// 划词按钮的淡入淡出动画
.fade-enter-active,
.fade-leave-active {
  transition: all 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>