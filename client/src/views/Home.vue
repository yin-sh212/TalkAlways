<template>
  <div class="home-container">
    <n-card title="欢迎使用智慧能源管理平台">
      <n-space vertical size="large">
        <n-alert type="info" title="平台简介">
          这是一个基于 Vue 3 + TypeScript + Naive UI 的智慧能源管理平台，提供能耗监控、数据分析、告警管理等功能。
        </n-alert>

        <n-descriptions bordered :column="2">
          <n-descriptions-item label="用户名">
            {{ userStore.userInfo?.username }}
          </n-descriptions-item>
          <n-descriptions-item label="邮箱">
            {{ userStore.userInfo?.email }}
          </n-descriptions-item>
          <n-descriptions-item label="用户 ID">
            {{ userStore.userInfo?.id }}
          </n-descriptions-item>
          <n-descriptions-item label="注册时间">
            {{ userStore.userInfo?.createdAt || '暂无' }}
          </n-descriptions-item>
        </n-descriptions>

        <n-grid :cols="3" :x-gap="16" :y-gap="16">
          <n-grid-item>
            <n-card hoverable @click="router.push('/overview')" style="cursor: pointer;">
              <template #header>
                <n-space align="center">
                  <n-icon size="24" color="#18a058">
                    <Home />
                  </n-icon>
                  <span>总览</span>
                </n-space>
              </template>
              <n-text depth="3">查看能源使用概况和关键指标</n-text>
            </n-card>
          </n-grid-item>
          
          <n-grid-item>
            <n-card hoverable @click="router.push('/analysis')" style="cursor: pointer;">
              <template #header>
                <n-space align="center">
                  <n-icon size="24" color="#1890ff">
                    <Analytics />
                  </n-icon>
                  <span>分析</span>
                </n-space>
              </template>
              <n-text depth="3">深入分析能耗数据和趋势</n-text>
            </n-card>
          </n-grid-item>
          
          <n-grid-item>
            <n-card hoverable @click="router.push('/alarm')" style="cursor: pointer;">
              <template #header>
                <n-space align="center">
                  <n-icon size="24" color="#f5222d">
                    <AlertCircle />
                  </n-icon>
                  <span>告警</span>
                </n-space>
              </template>
              <n-text depth="3">管理和处理系统告警信息</n-text>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { Home, Analytics, AlertCircle } from '@vicons/ionicons5'

const router = useRouter()
const userStore = useUserStore()
</script>

<style scoped lang="scss">
.home-container {
  width: 100%;
  height: 100%;
  padding: 24px;
  background: var(--bg-color);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  transition: background 0.3s ease;
}

:deep(.n-card) {
  max-width: 1200px;
  width: 100%;
}
</style>
