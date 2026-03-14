import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User } from '@/types/user'
import * as userApi from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // 状态 - 添加错误处理，兼容旧的 localStorage 数据
  const token = ref<string>(localStorage.getItem('token') || '')
  
  // 安全地解析 localStorage 中的用户信息
  let storedUser: User | null = null
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      storedUser = JSON.parse(userStr)
    }
  } catch (error) {
    console.warn('Failed to parse stored user data, clearing invalid data')
    localStorage.removeItem('user')
  }
  
  const userInfo = ref<User | null>(storedUser)

  // 登录
  const loginAction = async (username: string, password: string) => {
    try {
      const response = await userApi.login({ username, password })
      const { access_token, user_info } = response.data.data

      // 保存 token 和用户信息
      token.value = access_token
      userInfo.value = user_info
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(user_info))

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
      const { access_token, user_info } = response.data.data

      // 保存 token 和用户信息
      token.value = access_token
      userInfo.value = user_info
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(user_info))

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

  const setBuildingId = (buildingId: string) => {
    buildingId.value = buildingId
  }

  return {
    token,
    userInfo,
    loginAction,
    registerAction,
    logoutAction,
    setBuildingId
  }
})
