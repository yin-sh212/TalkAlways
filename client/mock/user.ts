import { MockMethod } from 'vite-plugin-mock'

// 模拟用户数据库
const users = [
  {
    id: '1',
    username: 'admin',
    email: 'admin@talkalways.com',
    password: '123456',
    avatar: '',
    createdAt: '2024-01-01 10:00:00'
  },
  {
    id: '2',
    username: 'test',
    email: 'test@talkalways.com',
    password: '123456',
    avatar: '',
    createdAt: '2024-01-02 10:00:00'
  }
]

// 生成 token
function generateToken(username: string) {
  return `mock-token-${username}-${Date.now()}`
}

export default [
  // 用户登录
  {
    url: '/api/user/login',
    method: 'post',
    response: ({ body }) => {
      const { username, password } = body
      const user = users.find(u => u.username === username)

      if (!user) {
        return {
          code: 400,
          message: '用户不存在',
          data: null
        }
      }

      if (user.password !== password) {
        return {
          code: 400,
          message: '密码错误',
          data: null
        }
      }

      const { password: _, ...userInfo } = user
      const token = generateToken(username)

      return {
        code: 200,
        message: '登录成功',
        data: {
          token,
          user: userInfo
        }
      }
    }
  },

  // 用户注册
  {
    url: '/api/user/register',
    method: 'post',
    response: ({ body }) => {
      const { username, email, password } = body

      // 检查用户名是否已存在
      const existUser = users.find(u => u.username === username)
      if (existUser) {
        return {
          code: 400,
          message: '用户名已存在',
          data: null
        }
      }

      // 检查邮箱是否已存在
      const existEmail = users.find(u => u.email === email)
      if (existEmail) {
        return {
          code: 400,
          message: '邮箱已被注册',
          data: null
        }
      }

      // 创建新用户
      const newUser = {
        id: String(users.length + 1),
        username,
        email,
        password,
        avatar: '',
        createdAt: new Date().toLocaleString('zh-CN')
      }

      users.push(newUser)

      const { password: _, ...userInfo } = newUser
      const token = generateToken(username)

      return {
        code: 200,
        message: '注册成功',
        data: {
          token,
          user: userInfo
        }
      }
    }
  },

  // 获取用户信息
  {
    url: '/api/user/info',
    method: 'get',
    response: ({ headers }) => {
      const token = headers?.authorization?.replace('Bearer ', '')

      if (!token) {
        return {
          code: 401,
          message: '未授权',
          data: null
        }
      }

      // 从 token 中提取用户名
      const username = token.split('-')[2]
      const user = users.find(u => u.username === username)

      if (!user) {
        return {
          code: 404,
          message: '用户不存在',
          data: null
        }
      }

      const { password: _, ...userInfo } = user

      return {
        code: 200,
        message: '获取成功',
        data: userInfo
      }
    }
  },

  // 退出登录
  {
    url: '/api/user/logout',
    method: 'post',
    response: () => {
      return {
        code: 200,
        message: '退出成功',
        data: null
      }
    }
  }
] as MockMethod[]
