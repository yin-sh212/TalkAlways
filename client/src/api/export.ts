import http from './http'

// 导出CSV
export const exportCSV = (params: { building_id?: string; start_date?: string; end_date?: string }) => {
  return http.get('/export/csv', { 
    params, 
    responseType: 'blob' 
  })
}

// 导出Excel
export const exportExcel = (params: { building_id?: string; start_date?: string; end_date?: string }) => {
  return http.get('/export/excel', { 
    params, 
    responseType: 'blob' 
  })
}

// 导出PDF
export const exportPDF = (params: { building_id?: string; start_date?: string; end_date?: string }) => {
  return http.get('/export/pdf', { 
    params, 
    responseType: 'blob' 
  })
}