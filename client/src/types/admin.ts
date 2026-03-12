// 数据管理相关类型定义

// 上传历史记录
export interface UploadHistory {
  id: string
  filename: string
  file_size: number
  upload_time: string
  status: 'success' | 'failed' | 'processing'
  message?: string
  // ... 其他上传记录属性
}

// CSV模板信息
export interface CSVTemplates {
  energy: {
    fields: string[]
    sample: any[]
  }
  device: {
    fields: string[]
    sample: any[]
  }
  // ... 其他模板类型
}