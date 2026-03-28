<template>
  <n-config-provider :theme="theme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-layout class="app-layout">
            <!-- 登录页面不显示导航栏 -->
            <template v-if="!isLoginPage">
              <Navbar />
            </template>
            
            <n-layout-content class="app-content">
              <router-view v-slot="{ Component, route }">
                <keep-alive>
                  <component :is="Component" :key="route.fullPath" v-if="route.meta.keepAlive" />
                </keep-alive>
                <component :is="Component" :key="route.fullPath" v-if="!route.meta.keepAlive" />
              </router-view>
            </n-layout-content>
            
            <!-- AI 悬浮球 - 全局可用 -->
            <AIFloatingBall />
          </n-layout>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider, NLayout, NLayoutContent, darkTheme, GlobalThemeOverrides } from 'naive-ui'
import Navbar from '@/components/common/Navbar.vue'
import AIFloatingBall from '@/components/common/AIFloatingBall.vue'

// 声明全局 Window 类型
declare global {
  interface Window {
    setTheme: (dark: boolean) => void
    isDark: { value: boolean }
  }
}

const route = useRoute()

onMounted(() => {
  console.log('[App] 应用已挂载，当前路由:', route.path)
})

// 判断是否是登录页面
const isLoginPage = computed(() => route.path === '/login')

// 主题状态 - 直接跟随浏览器外观
const isDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)

// 计算主题
const theme = computed(() => isDark.value ? darkTheme : null)

// 自定义主题覆盖（可选）
const themeOverrides = ref<GlobalThemeOverrides>({
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad74',
    primaryColorPressed: '#0c7a43',
  },
})

// 暴露切换主题方法给全局（保留以兼容现有代码）
const setTheme = (dark: boolean) => {
  isDark.value = dark
  
  // 同步更新 html 的 data-theme 属性（用于自定义 CSS 变量）
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
}

// 初始化主题
if (isDark.value) {
  document.documentElement.setAttribute('data-theme', 'dark')
}

// 将 setTheme 挂载到 window，方便其他地方调用
window.setTheme = setTheme
window.isDark = { value: isDark.value }

// 同步更新 window.isDark 的响应式值
watch(isDark, (newVal) => {
  window.isDark.value = newVal
})

// 监听浏览器外观变化 - 始终跟随系统主题
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  setTheme(e.matches)
})

</script>

<style>
/* 浅色主题变量（默认） */
:root {
  --bg-color: #f0f2f5;
  --card-bg: #ffffff;
  --text-primary: #333333;
  --text-secondary: #666666;
  --border-color: #e8e8e8;
}

/* 深色主题变量 */
[data-theme='dark'] {
  --bg-color: #1a1a1a;
  --card-bg: #242424;
  --text-primary: rgba(255, 255, 255, 0.9);
  --text-secondary: rgba(255, 255, 255, 0.65);
  --border-color: #424242;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg-color);
  color: var(--text-primary);
  transition: background 0.3s ease, color 0.3s ease;
}

.app-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.app-content {
  flex: 1;
  overflow: auto;
}
</style>
