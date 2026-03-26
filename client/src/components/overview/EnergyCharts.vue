<template>
  <n-grid :cols="2" :x-gap="16" :y-gap="16" class="chart-grid">
    <n-grid-item>
      <n-card
        title="各建筑能耗占比"
        :bordered="false"
        content-style="padding: 20px;"
      >
        <template #header-extra>
          <n-tooltip>
            <template #trigger>
              <n-icon
                size="18"
                style="cursor: pointer; color: #18a058"
                :component="LinkIcon"
              />
            </template>
            点击环形图的某个建筑，其他图表将联动显示该建筑数据
          </n-tooltip>
        </template>
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="pieChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card
        title="24 小时能耗分布"
        :bordered="false"
        content-style="padding: 20px;"
      >
        <n-skeleton v-if="loading" :rows="3" />
        <div v-else ref="distributionChartRef" class="chart-container"></div>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import {
  ref,
  onMounted,
  onUnmounted,
  watch,
  nextTick,
  getCurrentInstance,
} from "vue";
import * as echarts from "echarts";
import { LinkOutline as LinkIcon } from "@vicons/ionicons5";
import { useMessage } from "naive-ui";
import {
  getDonutChartConfig,
  getLineChartConfig,
  CHART_COLORS,
} from "@/utils/echarts-config";

interface TrendDataItem {
  date: string;
  energy: number;
}

interface Props {
  loading: boolean;
  buildingEnergy: any[];
  trendData: TrendDataItem[];
  distributionData?: {
    categories: string[];
    series: Array<{
      name: string;
      type: string;
      data: number[];
      areaStyle?: any;
      lineStyle?: any;
    }>;
  };
}

const props = defineProps<Props>();

// 定义事件
const emit = defineEmits<{
  (e: "buildingClick", buildingName: string): void;
}>();

const instance = getCurrentInstance();

// 重试配置
const MAX_RETRY_COUNT = 5;
const RETRY_DELAY = 300;

// 图表引用和实例管理
const pieChartRef = ref<HTMLElement | null>(null);
const distributionChartRef = ref<HTMLElement | null>(null);
const trendChartRef = ref<HTMLElement | null>(null);

// 使用 Map 统一管理所有图表实例，便于批量管理
const chartInstances = new Map<
  "pie" | "distribution" | "trend",
  echarts.ECharts | null
>();
chartInstances.set("pie", null);
chartInstances.set("distribution", null);
chartInstances.set("trend", null);

// 重试计数器
const retryCounts = {
  pie: 0,
  distribution: 0,
  trend: 0,
};

// 安全的图表初始化函数 - 带重试机制和尺寸检查
const safeInitChart = async (
  chartType: "pie" | "distribution" | "trend",
  containerRef: typeof pieChartRef,
  initFn: () => void,
): Promise<boolean> => {
  // 检查组件是否仍活跃
  if (!instance || !instance.isMounted) {
    console.warn(`[EnergyCharts] 组件未挂载，跳过 ${chartType} 初始化`);
    return false;
  }

  const container = containerRef.value;

  // 容器不存在时的兜底逻辑
  if (!container) {
    console.warn(`[EnergyCharts] ${chartType} 容器不存在，等待 DOM 创建`);
    retryCounts[chartType]++;

    if (retryCounts[chartType] >= MAX_RETRY_COUNT) {
      console.error(
        `[EnergyCharts] ${chartType} 重试次数已达上限 (${MAX_RETRY_COUNT})，停止重试`,
      );
      return false;
    }

    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY));
    return safeInitChart(chartType, containerRef, initFn);
  }

  // 检查容器尺寸 - 等待下一帧确保布局完成
  await nextTick();
  await new Promise(resolve => setTimeout(resolve, 100)); // 额外等待 100ms 让布局完成
  
  if (container.offsetWidth === 0 || container.offsetHeight === 0) {
    console.warn(
      `[EnergyCharts] ${chartType} 容器尺寸为 0 (${container.offsetWidth}x${container.offsetHeight})，等待布局完成`,
    );
    retryCounts[chartType]++;

    if (retryCounts[chartType] >= MAX_RETRY_COUNT) {
      console.error(
        `[EnergyCharts] ${chartType} 重试次数已达上限 (${MAX_RETRY_COUNT})，停止重试`,
      );
      return false;
    }

    // 等待布局完成后重试
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY * 2));
    return safeInitChart(chartType, containerRef, initFn);
  }

  // 重置重试计数器
  retryCounts[chartType] = 0;

  // 销毁旧实例（如果存在）
  const oldChart = chartInstances.get(chartType);
  if (oldChart && !oldChart.isDisposed()) {
    oldChart.dispose();
    chartInstances.set(chartType, null);
  }

  try {
    // 初始化新实例
    initFn();
    return true;
  } catch (error) {
    console.error(`[EnergyCharts] ${chartType} 初始化失败:`, error);
    return false;
  }
};

// 统一的图表初始化入口
const initAllCharts = async () => {
  // 并行初始化所有图表，提高性能
  await Promise.all([
    // 1. 环形图 - 各建筑能耗占比
    safeInitChart("pie", pieChartRef, () => {
      const hasData = props.buildingEnergy && props.buildingEnergy.length > 0;

      const chart = echarts.init(pieChartRef.value!);
      chartInstances.set("pie", chart);

      const donutConfig = getDonutChartConfig(
        hasData
          ? props.buildingEnergy.map((item) => ({
              value: item.value,
              name: item.name,
            }))
          : [],
        { title: "能耗占比" },
      );

      chart.setOption(donutConfig);

      // 添加点击事件监听
      chart.on("click", (params: any) => {
        if (params.data?.name) {
          emit("buildingClick", params.data.name);
        }
      });
    }),

    // 2. 折线图 - 24 小时能耗分布
    safeInitChart("distribution", distributionChartRef, () => {
      const chart = echarts.init(distributionChartRef.value!);
      chartInstances.set("distribution", chart);

      const distData = props.distributionData;

      const seriesData = (distData?.series || []).map((s) => ({
        name: s.name,
        data: s.data,
        areaStyle: !!s.areaStyle,
        smooth: true,
        color: CHART_COLORS.primary,
      }));

      const distConfig = getLineChartConfig(
        distData?.categories || [],
        seriesData,
        {
          yAxisName: "能耗 (kWh)",
          tooltipFormatter: "{b}: {c} kWh",
        },
      );

      chart.setOption(distConfig);
    }),
  ]);
};

// 监听 props 变化，重新初始化图表
watch(
  () => [props.loading, props.buildingEnergy, props.distributionData],
  async ([loading, buildingEnergy, distributionData]) => {
    if (loading) {
      return;
    }

    await initAllCharts();
  },
  { immediate: true },
);

// 监听窗口大小变化，重新调整图表尺寸
const resizeObserver = new ResizeObserver(() => {
  chartInstances.forEach((chart) => {
    if (chart) {
      chart.resize();
    }
  });
});

onMounted(() => {
  resizeObserver.observe(document.body);
});

onUnmounted(() => {
  resizeObserver.disconnect();
  chartInstances.forEach((chart) => {
    if (chart) {
      chart.dispose();
    }
  });
});

</script>

<style scoped>
.chart-grid {
  width: 100%;
  height: 100%;
}

.chart-container {
  width: 100%;
  min-height: 200px;
  height: 280px;
}

</style>
