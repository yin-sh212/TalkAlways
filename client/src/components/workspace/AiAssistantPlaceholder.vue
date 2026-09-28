<template>
  <div class="chat-wrapper">
    <!-- 消息列表 -->
    <div ref="messagesContainerRef" class="messages-container">
      <transition-group name="message-fade">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.type">
          <div class="message-avatar">
            <n-icon v-if="msg.type === 'user'" :component="Person" size="24" />
            <n-icon v-else :component="Sparkles" size="24" color="#1890ff" />
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <n-text v-if="msg.type === 'loading'" depth="3">
                <n-spin size="small" /> 思考中...
              </n-text>
              <markdown-renderer v-else :content="msg.content" />
            </div>
            <!-- 引用来源：仅助手消息且命中语料（sources 非空）时展示。
                 无引用（mode=llm 降级）时整块不渲染。 -->
            <div v-if="msg.sources && msg.sources.length" class="message-sources">
              <n-collapse>
                <n-collapse-item :title="`引用来源（${msg.sources.length}）`" name="sources">
                  <div v-for="(src, si) in msg.sources" :key="si" class="source-item">
                    <n-tag size="small" :bordered="false" type="info">{{ src.title }}</n-tag>
                    <n-text depth="3" class="source-snippet">{{ src.snippet }}</n-text>
                  </div>
                </n-collapse-item>
              </n-collapse>
            </div>
            <div class="message-time">{{ msg.time }}</div>
          </div>
        </div>
      </transition-group>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <n-input
        v-model:value="inputValue"
        type="textarea"
        placeholder="请输入问题，例如：'xxx建筑昨天的用电量是多少？' 或 '冷水机组高压报警怎么处理？'"
        :rows="3"
        :disabled="loading"
        @keydown.enter.exact.prevent="handleSend"
      >
        <template #suffix>
          <n-button
            type="primary"
            :disabled="!inputValue.trim() || loading"
            @click="handleSend"
          >
            <template #icon>
              <n-icon :component="Send" />
            </template>
            发送
          </n-button>
        </template>
      </n-input>

      <n-space class="quick-questions" :wrap="true">
        <n-tag
          v-for="(q, idx) in quickQuestions"
          :key="idx"
          checkable
          :checked="false"
          @update:checked="() => handleQuickQuestion(q)"
        >
          {{ q }}
        </n-tag>
      </n-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { Person, Sparkles, Send } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import { askQuestionStream } from '@/api/chat'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'
import type { SourceRef } from '@/types/chat'

interface Message {
  type: 'user' | 'assistant' | 'loading'
  content: string
  time: string
  sources?: SourceRef[]
}

const message = useMessage()
const messagesContainerRef = ref<HTMLElement | null>(null)
const inputValue = ref('')
const loading = ref(false)
let streamController: AbortController | null = null
const messages = ref<Message[]>([
  {
    type: 'assistant',
    content: '👋 您好！我是 AI 智能运维助手，很高兴为您服务～\n我可以帮您：\n- 📊 **能耗查询**：建筑用电量统计\n- 🔧 **故障诊断**：设备异常分析\n- 📚 **运维知识**：行业规范咨询\n请随时向我提问！',
    time: getCurrentTime()
  }
])

const quickQuestions = [
  'Eagle_education_Cassie 昨天用电量',
  '冷水机组高压报警处理',
  '空调系统运维规范',
  '能耗异常原因分析'
]

function getCurrentTime(): string {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  if (messagesContainerRef.value) {
    // 立即滚动到底部，不使用异步
    messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight
  }
}

async function handleSend() {
  const query = inputValue.value.trim()
  if (!query || loading.value) return

  // 添加用户消息
  messages.value.push({
    type: 'user',
    content: query,
    time: getCurrentTime()
  })

  inputValue.value = ''
  loading.value = true
  scrollToBottom()

  // 添加加载中消息
  const loadingIndex = messages.value.length
  messages.value.push({
    type: 'loading',
    content: '',
    time: getCurrentTime()
  })
  scrollToBottom()

  try {
    // 使用流式输出
    streamController = new AbortController()
    let fullContent = ''
    
    // 创建助手消息占位（先移除加载消息）
    messages.value.splice(loadingIndex, 1)
    const assistantMessageIndex = messages.value.length
    messages.value.push({
      type: 'assistant',
      content: '',
      time: getCurrentTime()
    })

    await askQuestionStream(
      query,
      (chunk) => {
        fullContent += chunk
        // 更新助手消息内容
        if (messages.value[assistantMessageIndex]) {
          messages.value[assistantMessageIndex].content = fullContent
          // 立即滚动到底部
          scrollToBottom()
        }
      },
      // 引用帧在 [DONE] 之前到达：写入该助手消息的 sources
      (sources) => {
        if (messages.value[assistantMessageIndex]) {
          messages.value[assistantMessageIndex].sources = sources
        }
      }
    )

    // 流式输出完成
    streamController = null

  } catch (error: any) {
    console.error('提问失败:', error)
    message.error('提问失败，请稍后重试')
    
    // 移除加载消息
    messages.value.splice(loadingIndex, 1)
    
    // 添加错误消息
    messages.value.push({
      type: 'assistant',
      content: `抱歉，处理您的问题时出现错误：${error.message || '未知错误'}`,
      time: getCurrentTime()
    })
    
    scrollToBottom()
  } finally {
    loading.value = false
    streamController = null
  }
}

function handleQuickQuestion(question: string) {
  inputValue.value = question
  handleSend()
}
</script>

<style scoped>
.chat-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--n-color-modal);
  border-radius: 8px;
  overflow: hidden;
  font-size: 16px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  min-height: 0;
}

.message-item {
  display: flex;
  margin-bottom: 16px;
  gap: 12px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(24, 144, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-item.user .message-avatar {
  background: rgba(82, 196, 26, 0.1);
}

.message-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.message-item.user .message-content {
  align-items: flex-end;
}

.message-bubble {
  padding: 8px 14px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  word-wrap: break-word;
  line-height: 1.6;
  font-size: 15px;
}

.message-item.user .message-bubble {
  background: #1890ff;
  color: white;
}

.message-time {
  font-size: 13px;
  color: var(--n-text-color-placeholder);
  padding: 0 8px;
}

/* 引用来源块：位于气泡与时间之间，宽度与气泡对齐 */
.message-sources {
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  padding: 0 12px;
  font-size: 13px;
}

.message-sources :deep(.n-collapse-item__header) {
  font-size: 13px;
  color: var(--n-text-color-placeholder);
}

.source-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.source-item:last-child {
  margin-bottom: 0;
}

.source-snippet {
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}

.input-area {
  flex-shrink: 0;
  padding: 16px;
  background: var(--n-color);
  border-top: 1px solid var(--n-border-color);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-questions {
  padding: 0 4px;
}

.message-fade-enter-active,
.message-fade-leave-active {
  transition: all 0.3s ease;
}

.message-fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.message-fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* Markdown 样式 */
:deep(.markdown-body) {
  font-size: 15px;
  line-height: 1.6;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3) {
  margin-top: 12px;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--n-text-color);
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  padding-left: 20px;
  margin: 6px 0;
}

:deep(.markdown-body code) {
  background: var(--n-color-modal);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  color: var(--n-text-color);
  font-size: 14px;
}

:deep(.markdown-body pre) {
  background: var(--n-color-modal);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 8px 0;
}

:deep(.markdown-body pre code) {
  background: transparent;
  padding: 0;
}

:deep(.markdown-body blockquote) {
  border-left: 3px solid var(--n-border-color);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--n-text-color-placeholder);
}

:deep(.markdown-body a) {
  color: #1890ff;
}

/* 深色模式优化 */
@media (prefers-color-scheme: dark) {
  .message-bubble {
    background: #2a2a2a;
    box-shadow: 0 1px 3px rgba(255, 255, 255, 0.1);
  }
  
  .message-item.user .message-bubble {
    background: #177ddc;
  }
}
</style>