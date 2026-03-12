import http from './http'

// 上传CSV文件
export const uploadCSV = (data: FormData) => {
  return http.post('/admin/upload', data, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 下载CSV模板
export const downloadTemplate = () => {
  return http.get('/admin/upload/template', {
    responseType: 'blob'
  })
}

// 获取上传历史
export const getUploadHistory = () => {
  return http.get('/admin/upload/history')
}