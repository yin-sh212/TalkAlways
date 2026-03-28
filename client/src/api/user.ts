import http from './http'
import type { 
  User, 
  LoginParams, 
  LoginResponse, 
  RegisterParams,
  ApiResponse
} from '@/types/user'

// 用户登录 - 使用 LoginParams 和 LoginResponse 类型
export const login = (data: LoginParams) => {
  return http.post<ApiResponse<LoginResponse>>('/user/login', data)
}

// 用户注册 - 使用 RegisterParams 类型
export const register = (data: RegisterParams) => {
  return http.post<ApiResponse<LoginResponse>>('/user/register', data)
}

// 获取当前用户信息 - 使用 User 类型
export const getCurrentUser = () => {
  return http.get<ApiResponse<User>>('/user/info')
}

// 更新用户信息 - 使用 User 类型
export const updateUserInfo = (data: Partial<User>) => {
  return http.put<ApiResponse<User>>('/user/info', data)
}

// 修改密码
export const changePassword = (data: { 
  old_password: string
  new_password: string
}) => {
  return http.post<ApiResponse<{ success: boolean }>>('/user/change-password', data)
}

// 退出登录
export const logout = () => {
  return http.post<ApiResponse<{ success: boolean }>>('/user/logout')
}

// 发送验证码
export const sendCode = (phone: string) => {
  return http.post<ApiResponse<{ success: boolean; message: string }>>('/user/send-code', { phone })
}

// 验证验证码
export const verifyCode = (phone: string, code: string) => {
  return http.post<ApiResponse<{ success: boolean; verified: boolean }>>('/user/verify-code', { phone, code })
}

// 重置密码
export const resetPassword = (data: { 
  phone: string
  code: string
  new_password: string
}) => {
  return http.post<ApiResponse<{ success: boolean }>>('/user/reset-password', data)
}
