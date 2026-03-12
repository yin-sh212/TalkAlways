// MCP协议相关类型定义

// MCP聊天请求
export interface MCPPrompt {
  messages: Array<{
    role: 'user' | 'assistant' | 'system'
    content: string
  }>
  tool_config?: {
    [key: string]: any
  }
}

// MCP工具信息
export interface MCPTool {
  name: string
  description: string
  parameters: {
    type: 'object'
    properties: {
      [key: string]: {
        type: string
        description: string
      }
    }
    required: string[]
  }
}