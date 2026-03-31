import http from './http'
import type { 
  ExportParams, 
  ExportTask, 
} from '@/types/export'

// 导出 CSV - 使用 ExportParams 类型
export const exportCSV = (params: ExportParams): Promise<any> => {
  return http.get('/export/csv', { 
    params, 
    responseType: 'blob' 
  })
}

// 导出 Excel - 使用 ExportParams 类型
export const exportExcel = (params: ExportParams): Promise<any> => {
  return http.get('/export/excel', { 
    params, 
    responseType: 'blob' 
  })
}

// 导出 PDF - 使用 ExportParams 类型
export const exportPDF = (params: ExportParams): Promise<any> => {
  return http.get('/export/pdf', { 
    params, 
    responseType: 'blob' 
  })
}

// 获取导出任务状态 - 使用 ExportTask 类型
export const getExportTaskStatus = (taskId: string): Promise<ExportTask> => {
  return http.get(`/export/task/${taskId}`)
}

// 取消导出任务
export const cancelExportTask = (taskId: string) => {
  return http.delete(`/export/task/${taskId}`)
}
