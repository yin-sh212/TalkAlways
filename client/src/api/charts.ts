import http from './http'
import type { ApiResponse } from '@/types/user'

// 获取趋势图数据
export const getTrendData = (params: { building_id?: string; days?: number; end_date?: string }) => {
  return http.get<ApiResponse<{
    categories: string[];
    series: Array<{
      name: string;
      type: string;
      data: number[];
      smooth?: boolean;
      lineStyle?: any;
    }>;
  }>>('/charts/trend', { params })
}

// 获取对比图数据
export const getComparisonData = (params: { building_ids?: string | string[]; start_date?: string; end_date?: string }) => {
  return http.get<ApiResponse<{
    categories: string[];
    series: Array<{
      name: string;
      type: string;
      data: number[];
    }>;
  }>>('/charts/comparison', { params })
}

// 获取分布图数据
export const getDistributionData = (params: { building_id?: string; date?: string }) => {
  return http.get<ApiResponse<{
    categories: string[];
    series: Array<{
      name: string;
      type: string;
      data: number[];
      areaStyle?: any;
    }>;
  }>>('/charts/distribution', { params })
}
