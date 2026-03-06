<template>
  <div class="login-container">
    <div class="login-card">
      <!-- Logo 和标题 -->
      <div class="header">
        <h1 class="title">TalkAlways</h1>
        <p class="subtitle">AI智语助手 - 让对话更智能</p>
      </div>

      <!-- 登录/注册切换 -->
      <n-tabs v-model:value="activeTab" size="large" animated>
        <!-- 登录表单 -->
        <n-tab-pane name="login" tab="登录">
          <n-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            label-placement="left"
            label-width="auto"
          >
            <n-form-item path="username" label="用户名">
              <n-input
                v-model:value="loginForm.username"
                placeholder="请输入用户名"
                size="large"
                @keyup.enter="handleLogin"
              />
            </n-form-item>

            <n-form-item path="password" label="密码">
              <n-input
                v-model:value="loginForm.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
                size="large"
                @keyup.enter="handleLogin"
              />
            </n-form-item>

            <n-button
              type="primary"
              size="large"
              block
              :loading="loginLoading"
              @click="handleLogin"
            >
              登录
            </n-button>
          </n-form>
        </n-tab-pane>

        <!-- 注册表单 -->
        <n-tab-pane name="register" tab="注册">
          <n-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-placement="left"
            label-width="auto"
          >
            <n-form-item path="username" label="用户名">
              <n-input
                v-model:value="registerForm.username"
                placeholder="请输入用户名"
                size="large"
              />
            </n-form-item>

            <n-form-item path="email" label="邮箱">
              <n-input
                v-model:value="registerForm.email"
                placeholder="请输入邮箱"
                size="large"
              />
            </n-form-item>

            <n-form-item path="password" label="密码">
              <n-input
                v-model:value="registerForm.password"
                type="password"
                show-password-on="click"
                placeholder="请输入密码"
                size="large"
              />
            </n-form-item>

            <n-form-item path="confirmPassword" label="确认密码">
              <n-input
                v-model:value="registerForm.confirmPassword"
                type="password"
                show-password-on="click"
                placeholder="请再次输入密码"
                size="large"
                @keyup.enter="handleRegister"
              />
            </n-form-item>

            <n-button
              type="primary"
              size="large"
              block
              :loading="registerLoading"
              @click="handleRegister"
            >
              注册
            </n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { useUserStore } from '@/store/user'

const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

// 当前激活的标签页
const activeTab = ref('login')

// 登录表单
const loginFormRef = ref<FormInst | null>(null)
const loginLoading = ref(false)
const loginForm = ref({
  username: '',
  password: ''
})

// 登录表单验证规则
const loginRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为 3-20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为 6-20 个字符', trigger: 'blur' }
  ]
}

// 注册表单
const registerFormRef = ref<FormInst | null>(null)
const registerLoading = ref(false)
const registerForm = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 注册表单验证规则
const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为 3-20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为 6-20 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value) => {
        return value === registerForm.value.password
      },
      message: '两次输入的密码不一致',
      trigger: 'blur'
    }
  ]
}

// 处理登录
const handleLogin = async () => {
  try {
    await loginFormRef.value?.validate()
    loginLoading.value = true

    const result = await userStore.loginAction(
      loginForm.value.username,
      loginForm.value.password
    )

    if (result.success) {
      message.success('登录成功')
      router.push('/')
    } else {
      message.error(result.message || '登录失败')
    }
  } catch (error) {
    console.error('表单验证失败', error)
  } finally {
    loginLoading.value = false
  }
}

// 处理注册
const handleRegister = async () => {
  try {
    await registerFormRef.value?.validate()
    registerLoading.value = true

    const result = await userStore.registerAction(registerForm.value)

    if (result.success) {
      message.success('注册成功，即将跳转')
      setTimeout(() => {
        router.push('/')
      }, 1000)
    } else {
      message.error(result.message || '注册失败')
    }
  } catch (error) {
    console.error('表单验证失败', error)
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100vw;
  height: 100vh;
  min-height: 100vh;
  background: #f5f7fa;
  position: fixed;
  top: 0;
  left: 0;
}

.login-card {
  width: 450px;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.title {
  font-size: 32px;
  font-weight: bold;
  color: #18a058;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 14px;
  color: #666;
}

:deep(.n-tabs-nav) {
  margin-bottom: 24px;
}

:deep(.n-form-item) {
  margin-bottom: 20px;
}

:deep(.n-button) {
  margin-top: 8px;
}
</style>
