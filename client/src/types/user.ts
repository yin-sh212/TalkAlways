// 用户相关类型定义

export interface User {
  user_id: string
  username: string
  phone?: string
  email?: string
  avatar?: string
}

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  email: string
  password: string
  confirmPassword: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_info: User
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}
