import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import type { ApiResponse } from '@/types/user'

// 创建 axios 实例
const http: AxiosInstance = axios.create({
  // baseURL: 'https://kellen-warty-kurt.ngrok-free.dev/api',
  baseURL: 'http://127.0.0.1:3000/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  },
  // 自定义参数序列化器，支持数组参数（如 dates=[a, b, c] -> dates=a&dates=b&dates=c）
  paramsSerializer: (params) => {
    if (!params) return ''
    const parts: string[] = []
    
    Object.entries(params).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        // 数组类型：key=value1&key=value2&key=value3
        value.forEach(v => {
          parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(v)}`)
        })
      } else if (value !== undefined && value !== null) {
        // 普通类型
        parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      }
    })
    
    return parts.join('&')
  }
})

// 请求拦截器
http.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    // 如果是 blob 类型，直接返回
    if (response.config.responseType === 'blob') {
      return response
    }
    
    const { data } = response

    // 根据业务状态码判断
    if (data.code === 0 || data.code === 200) {
      return response
    } else {
      // 业务错误
      return Promise.reject(new Error(data.message || '请求失败'))
    }
  },
  (error) => {
    // HTTP 错误
    if (error.response) {
      const { status } = error.response

      switch (status) {
        case 401:
          // 未授权，清除 token 并跳转到登录页
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          break
        case 403:
          console.error('没有权限访问')
          break
        case 404:
          console.error('请求的资源不存在')
          break
        case 500:
          console.error('服务器错误')
          break
        default:
          console.error('请求失败')
      }
    }

    return Promise.reject(error)
  }
)

export default http
