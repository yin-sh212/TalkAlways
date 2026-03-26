// 用户相关类型定义

export interface User {
  user_id: string
  name: string
  phone?: string
  email?: string
  avatar?: string
}

export interface LoginParams {
  account: string
  password: string
  login_type?: string
}

export interface RegisterParams {
  name: string
  phone?: string
  email?: string
  password: string
  confirmPassword?: string
}

export interface LoginResponse {
  code: number
  message: string
  access_token: string
  token_type: string
  expires_in: number
  user_info: {
    user_id: string
    name: string
    phone: string
    email: string
  }
}

export interface RegisterResponse {
  code: number
  message: string
  access_token: string
  token_type: string
  expires_in: number
  user_info: {
    user_id: string
    name: string
    phone: string
    email: string
  }
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
}
