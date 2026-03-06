import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User } from '@/types/user'
import * as userApi from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<User | null>(
    localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')!) : null
  )

  // 登录
  const loginAction = async (username: string, password: string) => {
    try {
      const response = await userApi.login({ username, password })
      const { token: newToken, user } = response.data.data

      // 保存 token 和用户信息
      token.value = newToken
      userInfo.value = user
      localStorage.setItem('token', newToken)
      localStorage.setItem('user', JSON.stringify(user))

      return { success: true }
    } catch (error: any) {
      return { success: false, message: error.message || '登录失败' }
    }
  }

  // 注册
  const registerAction = async (params: {
    username: string
    email: string
    password: string
    confirmPassword: string
  }) => {
    try {
      const response = await userApi.register(params)
      const { token: newToken, user } = response.data.data

      // 保存 token 和用户信息
      token.value = newToken
      userInfo.value = user
      localStorage.setItem('token', newToken)
      localStorage.setItem('user', JSON.stringify(user))

      return { success: true }
    } catch (error: any) {
      return { success: false, message: error.message || '注册失败' }
    }
  }

  // 退出登录
  const logoutAction = async () => {
    try {
      await userApi.logout()
    } catch (error) {
      console.error('退出登录失败', error)
    } finally {
      // 清除本地数据
      token.value = ''
      userInfo.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }

  return {
    token,
    userInfo,
    loginAction,
    registerAction,
    logoutAction
  }
})
