<template>
  <div class="home-container">
    <div class="header">
      <div class="logo">
        <h1>TalkAlways</h1>
        <span class="tag">AI智语助手</span>
      </div>
      <div class="user-info">
        <n-avatar round size="medium">
          {{ userStore.userInfo?.username?.charAt(0).toUpperCase() }}
        </n-avatar>
        <span class="username">{{ userStore.userInfo?.username }}</span>
        <n-button text @click="handleLogout">退出登录</n-button>
      </div>
    </div>

    <div class="content">
      <n-card title="欢迎使用 TalkAlways AI智语助手">
        <n-space vertical size="large">
          <n-alert type="info" title="项目简介">
            这是一个基于 Vue 3 + TypeScript + Naive UI 的 AI 辅助教学平台，提供智能对话、知识问答等功能。
          </n-alert>

          <n-descriptions bordered :column="2">
            <n-descriptions-item label="用户名">
              {{ userStore.userInfo?.username }}
            </n-descriptions-item>
            <n-descriptions-item label="邮箱">
              {{ userStore.userInfo?.email }}
            </n-descriptions-item>
            <n-descriptions-item label="用户ID">
              {{ userStore.userInfo?.id }}
            </n-descriptions-item>
            <n-descriptions-item label="注册时间">
              {{ userStore.userInfo?.createdAt || '暂无' }}
            </n-descriptions-item>
          </n-descriptions>

          <n-space>
            <n-button type="primary" size="large">
              开始对话
            </n-button>
            <n-button size="large">
              功能设置
            </n-button>
          </n-space>
        </n-space>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useDialog, useMessage } from 'naive-ui'
import { useUserStore } from '@/store/user'

const router = useRouter()
const dialog = useDialog()
const message = useMessage()
const userStore = useUserStore()

// 退出登录
const handleLogout = () => {
  dialog.warning({
    title: '退出登录',
    content: '确定要退出登录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      await userStore.logoutAction()
      message.success('已退出登录')
      router.push('/login')
    }
  })
}
</script>

<style scoped lang="scss">
.home-container {
  width: 100%;
  height: 100%;
  background: var(--bg-color);
  display: flex;
  flex-direction: column;
  transition: background 0.3s ease;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--card-bg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: background 0.3s ease, box-shadow 0.3s ease;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;

  h1 {
    font-size: 24px;
    font-weight: bold;
    color: #18a058;
    margin: 0;
  }

  .tag {
    padding: 4px 12px;
    background: #18a058;
    color: white;
    border-radius: 12px;
    font-size: 12px;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;

  .username {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
    transition: color 0.3s ease;
  }
}

.content {
  flex: 1;
  padding: 32px;
  overflow: auto;
}

:deep(.n-card) {
  max-width: 800px;
  margin: 0 auto;
}
</style>
