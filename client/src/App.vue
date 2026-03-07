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

// 主题状态 - 从 localStorage 读取
const isDark = ref(localStorage.getItem('theme') === 'dark')

// 计算主题
const theme = computed(() => isDark.value ? darkTheme : null)

// 自定义主题覆盖（可选）
const themeOverrides = ref<GlobalThemeOverrides>({
  common: {
    primaryColor: '#1890ff',
    primaryColorHover: '#40a9ff',
    primaryColorPressed: '#096dd9',
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

// 同步更新 window.isDark 的响应式值
watch(isDark, (newVal) => {
  window.isDark.value = newVal
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
