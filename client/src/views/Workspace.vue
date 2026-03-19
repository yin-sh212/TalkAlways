<template>
  <div class="workspace-container">
    <!-- 顶部标签页切换 -->
    <n-tabs v-model:value="activeTab" type="line" animated @update:value="handleTabChange">
       <!-- Tab 1: AI 助手 -->
      <n-tab-pane name="assistant" tab="AI 助手">
        <AiAssistantPlaceholder />
      </n-tab-pane>
     

      <!-- Tab 2: 运维知识库 -->
      <n-tab-pane name="knowledge" tab="运维知识库">
        <KnowledgeBase />
      </n-tab-pane>

      <!-- Tab 3: 设备信息 -->
      <n-tab-pane name="devices" tab="设备管理">
        <DeviceManagement />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DeviceManagement from '@/components/workspace/DeviceManagement.vue'
import KnowledgeBase from '@/components/workspace/KnowledgeBase.vue'
import AiAssistantPlaceholder from '@/components/workspace/AiAssistantPlaceholder.vue'

const activeTab = ref('assistant')

// 处理标签页切换
const handleTabChange = (tab: string) => {
  activeTab.value = tab
}

onMounted(() => {
  // 可以从 URL 参数中读取默认选中的 tab
  const urlParams = new URLSearchParams(window.location.search)
  const tab = urlParams.get('tab')
  if (tab && ['devices', 'knowledge', 'assistant'].includes(tab)) {
   activeTab.value = tab
  }
})
</script>

<style scoped>
.workspace-container {
  padding: 24px;
  background: var(--bg-color);
  min-height: calc(100vh - 64px);
}

:deep(.n-tabs) {
  .n-tabs-nav {
   background: var(--card-bg);
   padding: 0 16px;
    border-radius: 8px 8px 0 0;
  }
  
  .n-tabs-pane-wrapper {
   background: var(--card-bg);
    border-radius: 0 0 8px 8px;
  }
}
</style>
