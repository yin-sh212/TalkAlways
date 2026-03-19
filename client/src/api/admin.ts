import http from './http'

// 上传CSV文件
export const uploadCSV = (data: FormData) => {
  return http.post('/admin/upload', data, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 下载 CSV 模板
export const downloadTemplate = () => {
  return http.get('/admin/upload/template', {
    responseType: 'blob'
  })
}

// 获取上传历史
export const getUploadHistory = () => {
  return http.get('/admin/upload/history')
}

// 获取支持的文件格式
export const getSupportedFormats = () => {
  return http.get('/admin/supported-formats')
}

// ========== 知识库管理接口 ==========

// 新增文档参数
export interface AddDocumentParams {
  title: string
  category: string
  tags: string[]
  summary: string
  description: string
  solution: string
  notes: string[]
}

// 新增文档到知识库
export const addDocument = (data: AddDocumentParams) => {
  return http.post('/knowledge/add', data)
}