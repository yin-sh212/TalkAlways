import http from './http'
import type { 
  MCPPrompt, 
  MCPTool, 
  MCPToolCall,
  MCPResponse 
} from '@/types/mcp'
import type { ApiResponse } from '@/types/user'

// MCP 协议聊天 - 使用 MCPPrompt 和 MCPResponse 类型
export const mcpChat = (prompt: MCPPrompt) => {
  return http.post<MCPResponse>('/mcp/api/v1/chats', prompt)
}

// 列出 MCP 工具 - 使用 MCPTool 类型
export interface MCPToolsResponse {
  tools: MCPTool[]
}

export const listMcpTools = () => {
  return http.get<ApiResponse<MCPToolsResponse>>('/mcp/v1/tools')
}

// 调用 MCP 工具 - 使用 MCPToolCall 类型
export const callMcpTool = (toolCall: MCPToolCall) => {
  return http.post<MCPResponse>('/mcp/v1/tools/call', toolCall)
}

// 获取 MCP 工具详情
export const getMcpToolDetail = (toolName: string) => {
  return http.get<ApiResponse<MCPTool>>(`/mcp/v1/tools/${toolName}`)
}
