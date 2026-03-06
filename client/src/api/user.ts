import http from './http'
import type { LoginParams, RegisterParams, LoginResponse, ApiResponse, User } from '@/types/user'

// 用户登录
export const login = (params: LoginParams) => {
  return http.post<ApiResponse<LoginResponse>>('/user/login', params)
}

// 用户注册
export const register = (params: RegisterParams) => {
  return http.post<ApiResponse<LoginResponse>>('/user/register', params)
}

// 获取用户信息
export const getUserInfo = () => {
  return http.get<ApiResponse<User>>('/user/info')
}

// 退出登录
export const logout = () => {
  return http.post<ApiResponse>('/user/logout')
}
