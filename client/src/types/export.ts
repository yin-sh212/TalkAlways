// 报表导出相关类型定义

// 导出参数
export interface ExportParams {
  building_id?: string
  start_date?: string
  end_date?: string
  format?: 'csv' | 'excel' | 'pdf'
}

// 导出任务状态
export interface ExportTask {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  file_url?: string
  file_size?: number
}

// 导出响应
export interface ExportResponse {
  code: number
  message: string
  data: {
    download_url: string
    file_name: string
    file_size: number
  }
}
