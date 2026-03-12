import http from './http'

// MCP协议聊天
export const mcpChat = (data: { messages: any[]; tool_config?: any }) => {
  return http.post('/mcp/api/v1/chats', data)
}

// 列出MCP工具
export const listMcpTools = () => {
  return http.get('/mcp/v1/tools')
}