// MCP 协议相关类型定义

// MCP 聊天请求
export interface MCPPrompt {
  messages: Array<{
    role: 'user' | 'assistant' | 'system'
    content: string
  }>
  tool_config?: {
    [key: string]: any
  }
}

// MCP 工具信息
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

// MCP 工具调用参数
export interface MCPToolCall {
  tool_name: string
  arguments: Record<string, any>
}

// MCP 响应
export interface MCPResponse {
  code: number
  message: string
  data: {
    result: any
    tool_used?: string
  }
}
