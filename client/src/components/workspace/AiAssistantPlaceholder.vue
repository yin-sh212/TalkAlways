<template>
  <div class="ai-assistant">
    <!-- 功能预告卡片 -->
    <n-card
    title="🤖 AI 智能助手"
     :bordered="false"
      embedded
      style="margin-bottom: 20px;"
    >
      <template #header-extra>
        <n-tag type="warning" size="small">即将上线</n-tag>
      </template>
      
      <n-space vertical :size="16">
        <n-alert type="info" title="功能说明">
          基于先进的人工智能技术，为运维人员提供智能问答、故障诊断、知识推荐等服务。
          <br><strong>支持多模态交互</strong>：不仅限于文本，未来将支持图片、语音等多种交互方式。
        </n-alert>
        
        <n-grid :cols="3" :x-gap="16" :y-gap="16">
          <n-grid-item>
            <n-card embedded>
              <template #header>
                <n-space align="center">
                  <n-icon :component="Chatbubbles" size="24" color="#1890ff" />
                  <span>智能问答</span>
                </n-space>
              </template>
              <n-text depth="3" style="font-size: 14px;">
                7×24 小时在线解答设备运维相关问题，快速定位故障原因
              </n-text>
            </n-card>
          </n-grid-item>
          
          <n-grid-item>
            <n-card embedded>
              <template #header>
                <n-space align="center">
                  <n-icon :component="Images" size="24" color="#52c41a" />
                  <span>图像识别</span>
                </n-space>
              </template>
              <n-text depth="3" style="font-size: 14px;">
                上传设备照片，AI 自动识别设备型号、状态和潜在问题
              </n-text>
            </n-card>
          </n-grid-item>
          
          <n-grid-item>
            <n-card embedded>
              <template #header>
                <n-space align="center">
                  <n-icon :component="DocumentText" size="24" color="#fa8c16" />
                  <span>文档生成</span>
                </n-space>
              </template>
              <n-text depth="3" style="font-size: 14px;">
                自动生成维修报告、保养记录等文档，提高工作效率
              </n-text>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-space>
    </n-card>

    <!-- 占位对话界面（预留） -->
    <n-card title="对话界面（开发中）" :bordered="false" style="height: calc(100vh - 400px);">
      <div class="chat-placeholder">
        <n-empty
         description="AI 助手功能开发中，敬请期待..."
         size="large"
         style="margin-top: 100px;"
        >
          <template #icon>
            <n-icon :component="Sparkles" size="80" color="#1890ff" />
          </template>
        </n-empty>
        
        <n-space vertical :size="20" style="margin-top: 40px; max-width: 600px; margin-left: auto; margin-right: auto;">
          <n-alert type="success" title="规划功能">
            <ul style="margin: 0; padding-left: 20px;">
              <li>💬 多轮对话上下文理解</li>
              <li>🖼️ 图片上传与识别（设备铭牌、故障现象）</li>
              <li>📊 数据分析和趋势预测</li>
              <li>🔧 维修方案智能推荐</li>
              <li>📱 移动端语音交互</li>
            </ul>
          </n-alert>
          
          <n-alert type="warning" title="技术架构预留">
            <strong>后端接口预留：</strong>
            <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; margin-top: 8px; font-size: 12px;">
POST /api/ai/chat          - 文本对话
POST /api/ai/vision        - 图像识别（待实现）
POST /api/ai/voice         - 语音交互（待实现）
GET /api/ai/conversations - 获取会话历史
            </pre>
          </n-alert>
        </n-space>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { Chatbubbles, Images, DocumentText, Sparkles } from '@vicons/ionicons5'

</script>

<style scoped>
.ai-assistant {
  min-height: 100%;
}

.chat-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

:deep(.n-alert) {
  width: 100%;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
