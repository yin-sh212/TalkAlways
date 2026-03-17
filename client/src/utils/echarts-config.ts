/**
 * ECharts 基础配置工具
 * 提供常用的饼图、折线图、柱状图基础配置
 */

import type { EChartsOption } from 'echarts';

/**
 * 颜色主题配置
 */
export const CHART_COLORS = {
  primary: '#18a058',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  info: '#1890ff',
  palette: [
    '#18a058',
    '#1890ff',
    '#722ed1',
    '#f6bd16',
    '#f759ab',
    '#52c41a',
    '#13c2c2',
    '#fa8c16',
  ],
};

/**
 * 通用网格配置（带右侧图例空间）
 */
export const DEFAULT_GRID = {
  left: '3%',
  right: '15%',
  bottom: '3%',
  containLabel: true,
};

/**
 * 通用 Tooltip 配置
 */
export const DEFAULT_TOOLTIP = {
  trigger: 'axis' as const,
  axisPointer: {
    type: 'shadow',
  },
};

/**
 * 标准图例配置（避免与图表重合）
 */
export const DEFAULT_LEGEND = {
  orient: 'vertical' as const,
  right: '8%',
  top: 'center',
  itemWidth: 12,
  itemHeight: 12,
  textStyle: {
    fontSize: 12,
  },
};

/**
 * 基础折线图配置
 * @param xAxisData - X 轴数据
 * @param seriesData - 系列数据
 * @param options - 可选配置项
 */
export function getLineChartConfig(
  xAxisData: string[],
  seriesData: Array<{
    name: string;
    data: number[];
    color?: string;
    areaStyle?: boolean;
    smooth?: boolean;
  }>,
  options: {
    title?: string;
    yAxisName?: string;
    tooltipFormatter?: string;
    grid?: any;
  } = {},
): EChartsOption {
  const {
    title = '',
    yAxisName = '数值',
    tooltipFormatter = '{b}: {c}',
    grid = DEFAULT_GRID,
  } = options;

  return {
    title: title ? { text: title, left: 'center' } : undefined,
    tooltip: {
      trigger: 'axis' as const,
      formatter: tooltipFormatter,
    },
    grid,
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: xAxisData,
      axisLabel: {
        rotate: 0,
      },
    },
    yAxis: {
      type: 'value' as const,
      name: yAxisName,
      axisLabel: {
        formatter: '{value}',
      },
      splitLine: {
        lineStyle: {
          type: 'dashed',
        },
      },
    },
    series: seriesData.map((series) => ({
      name: series.name,
      type: 'line' as const,
      smooth: series.smooth ?? true,
      data: series.data,
      itemStyle: {
        color: series.color || CHART_COLORS.primary,
      },
      areaStyle: series.areaStyle
        ? { opacity: 0.3 }
        : undefined,
      lineStyle: {
        width: 3,
      },
    })),
  };
}

/**
 * 基础柱状图配置
 * @param xAxisData - X 轴数据
 * @param seriesData - 系列数据
 * @param options - 可选配置项
 */
export function getBarChartConfig(
  xAxisData: string[],
  seriesData: Array<{
    name: string;
    data: number[];
    color?: string;
  }>,
  options: {
    title?: string;
    yAxisName?: string;
    tooltipFormatter?: string;
    grid?: any;
    barWidth?: string | number;
  } = {},
): EChartsOption {
  const {
    title = '',
    yAxisName = '数值',
    tooltipFormatter = '{b}: {c}',
    grid = DEFAULT_GRID,
    barWidth = '60%',
  } = options;

  return {
    title: title ? { text: title, left: 'center' } : undefined,
    tooltip: {
      trigger: 'axis' as const,
      formatter: tooltipFormatter,
    },
    grid,
    xAxis: {
      type: 'category' as const,
      data: xAxisData,
      axisLabel: {
        rotate: 45,
      },
    },
    yAxis: {
      type: 'value' as const,
      name: yAxisName,
      axisLabel: {
        formatter: '{value}',
      },
      splitLine: {
        lineStyle: {
          type: 'dashed',
        },
      },
    },
    series: seriesData.map((series) => ({
      name: series.name,
      type: 'bar' as const,
      data: series.data,
      barWidth,
      itemStyle: {
        color: series.color || CHART_COLORS.primary,
        borderRadius: [5, 5, 0, 0],
      },
    })),
  };
}

/**
 * 基础饼图配置
 * @param data - 饼图数据
 * @param options - 可选配置项
 */
export function getPieChartConfig(
  data: Array<{
    name: string;
    value: number;
  }>,
  options: {
    title?: string;
    center?: string[];
    radius?: string[];
    tooltipFormatter?: string;
    showLegend?: boolean;
  } = {},
): EChartsOption {
  const {
    title = '',
    center = ['50%', '50%'],
    radius = ['40%', '70%'],
    tooltipFormatter = '{b}: {c} ({d}%)',
    showLegend = true,
  } = options;

  return {
    title: title ? { text: title, left: 'center' } : undefined,
    tooltip: {
      trigger: 'item' as const,
      formatter: tooltipFormatter,
    },
    legend: showLegend
      ? {
          orient: 'vertical' as const,
          right: '8%',
          top: 'center',
          itemWidth: 12,
          itemHeight: 12,
          textStyle: {
            fontSize: 12,
          },
        }
      : undefined,
    series: [
      {
        name: title || '数据分布',
        type: 'pie' as const,
        radius,
        center: ['45%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
          color: (params: any) => {
            const colors = CHART_COLORS.palette;
            return colors[params.dataIndex % colors.length];
          },
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        labelLine: {
          show: false,
        },
        data,
      },
    ],
  };
}

/**
 * 环形图配置（带选中效果）
 * @param data - 环形图数据
 * @param options - 可选配置项
 */
export function getDonutChartConfig(
  data: Array<{
    name: string;
    value: number;
  }>,
  options: {
    title?: string;
    onItemSelect?: (itemName: string) => void;
  } = {},
): EChartsOption {
  const { title = '' } = options;

  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: '{b}: {c} ({d}%)',
    },
    legend: DEFAULT_LEGEND,
    series: [
      {
        name: title || '占比',
        type: 'pie' as const,
        radius: ['40%', '70%'],
        center: ['33%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
          color: (params: any) => {
            const colors = CHART_COLORS.palette;
            return colors[params.dataIndex % colors.length];
          },
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        labelLine: {
          show: false,
        },
        data,
        selectedMode: 'single',
        selectedOffset: 10,
      },
    ],
  };
}

/**
 * 基础饼图配置（通用版本，支持左右图例）
 * @param data - 饼图数据
 * @param options - 可选配置项
 */
export function getBasePieChartConfig(
  data: Array<{
    name: string;
    value: number;
  }>,
  options: {
    title?: string;
    radius?: string[];
    center?: string[];
    tooltipFormatter?: string;
    showLegend?: boolean;
    legendPosition?: 'left' | 'right';
  } = {},
): EChartsOption {
  const {
    title = '',
    radius = ['40%', '70%'],
    center = ['45%', '50%'],
    tooltipFormatter = '{b}: {c} ({d}%)',
    showLegend = true,
    legendPosition = 'right',
  } = options;

  return {
    title: title ? { text: title, left: 'center' } : undefined,
    tooltip: {
      trigger: 'item' as const,
      formatter: tooltipFormatter,
    },
    legend: showLegend
      ? {
          ...DEFAULT_LEGEND,
          right: legendPosition === 'right' ? '8%' : 'auto',
          left: legendPosition === 'left' ? '8%' : 'auto',
        }
      : undefined,
    series: [
      {
        name: title || '数据分布',
        type: 'pie' as const,
        radius,
        center,
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
          color: (params: any) => {
            const colors = CHART_COLORS.palette;
            return colors[params.dataIndex % colors.length];
          },
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        labelLine: {
          show: false,
        },
        data,
      },
    ],
  };
}
