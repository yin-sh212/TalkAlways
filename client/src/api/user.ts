import http from "./http";
import type {
  User,
  LoginParams,
  RegisterParams,
  LoginResponse,
  RegisterResponse,
  ApiResponse,
} from "@/types/user";

// 用户登录
export const login = (params: LoginParams) => {
  return http.post<LoginResponse>("/auth/login", params);
};

// 用户注册
export const register = (params: RegisterParams) => {
  return http.post<RegisterResponse>("/auth/register", params);
};

// 获取用户信息
export const getUserInfo = () => {
  return http.get<ApiResponse<User>>("/user/info");
};

// 退出登录
export const logout = () => {
  return http.post<ApiResponse>("/auth/logout");
};
