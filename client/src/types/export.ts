// 报表导出相关类型定义

// 导出参数
export interface ExportParams {
  building_id?: string
  start_date?: string
  end_date?: string
  format?: 'csv' | 'excel' | 'pdf'
}