<template>
  <n-config-provider :theme="theme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider, darkTheme, GlobalThemeOverrides } from 'naive-ui'

// 声明全局 Window 类型
declare global {
  interface Window {
    setTheme: (dark: boolean) => void
    isDark: { value: boolean }
  }
}

// 主题状态 - 优先从 localStorage 读取，如果没有则跟随浏览器外观
const getInitialTheme = () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    // 用户手动设置过，使用用户的设置
    return savedTheme === 'dark'
  } else {
    // 没有手动设置过，跟随浏览器外观
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  }
}

const isDark = ref(getInitialTheme())

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

// 暴露切换主题方法给全局
const setTheme = (dark: boolean) => {
  isDark.value = dark
  localStorage.setItem('theme', dark ? 'dark' : 'light')
  
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

// 监听浏览器主题变化（仅在用户未手动设置时生效）
watch(isDark, (newVal) => {
  window.isDark.value = newVal
})

// 监听浏览器外观变化
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  // 只有当用户没有手动设置主题时，才跟随浏览器变化
  if (!localStorage.getItem('theme')) {
    setTheme(e.matches)
  }
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
</style>