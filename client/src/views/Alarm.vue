<template>
  <div class="alarm-container">
    <!-- 顶部查询条件栏 -->
    <div class="query-section">
      <n-card :bordered="false" content-style="padding: 20px;">
        <n-collapse default-expanded-names="query-form" arrow-placement="right">
          <n-collapse-item title="查询条件" name="query-form">
            <n-form
              :model="queryForm"
              :rules="queryRules"
              ref="queryFormRef"
              label-placement="top"
            >
              <n-grid :cols="4" :x-gap="16" :y-gap="16">
                <!-- 建筑选择 -->
                <n-grid-item>
                  <n-form-item label="建筑选择" path="buildings">
                    <n-select
                      v-model:value="queryForm.buildings"
                      placeholder="请选择建筑"
                      filterable
                      multiple
                      :options="buildingOptions"
                    />
                  </n-form-item>
                </n-grid-item>

                <!-- 告警级别 -->
                <n-grid-item>
                  <n-form-item label="告警级别" path="severity">
                    <n-select
                      v-model:value="queryForm.severity"
                      placeholder="请选择级别"
                      multiple
                      :options="severityOptions"
                    />
                  </n-form-item>
                </n-grid-item>

                <!-- 告警类型 -->
                <n-grid-item>
                  <n-form-item label="告警类型" path="alarmType">
                    <n-select
                      v-model:value="queryForm.alarmType"
                      placeholder="请选择类型"
                      multiple
                      :options="alarmTypeOptions"
                    />
                  </n-form-item>
                </n-grid-item>

                <!-- 时间范围 -->
                <n-grid-item>
                  <n-form-item label="时间范围" path="timeRange">
                    <n-space :size="8" style="width: 100%">
                      <n-date-picker
                        v-model:value="queryForm.timeRange"
                        type="daterange"
                        placeholder="选择日期范围"
                        style="flex: 1"
                      />
                      <n-space :size="4">
                        <n-button size="small" @click="setQuickTime('today')"
                          >今日</n-button
                        >
                        <n-button size="small" @click="setQuickTime('week')"
                          >本周</n-button
                        >
                        <n-button size="small" @click="setQuickTime('month')"
                          >本月</n-button
                        >
                      </n-space>
                    </n-space>
                  </n-form-item>
                </n-grid-item>
              </n-grid>

              <!-- 操作按钮 -->
              <n-space justify="end" style="margin-top: 16px">
                <n-button @click="handleReset">重置</n-button>
                <n-button
                  type="primary"
                  @click="() => handleQuery(false)"
                  :loading="queryLoading"
                >
                  查询
                </n-button>
              </n-space>
            </n-form>
          </n-collapse-item>
        </n-collapse>
      </n-card>
    </div>

    <!-- 告警统计指标卡 -->
    <div class="metrics-section">
      <AlarmKpiCards :metrics="metrics" :loading="metricsLoading" />
    </div>

    <!-- 告警图表分析 -->
    <div class="charts-section">
      <n-grid :cols="24" :x-gap="16" :y-gap="16">
        <n-grid-item :span="16">
          <AlarmTrend
            ref="alarmTrendRef"
            :trendData="trendData"
            :loading="chartLoading"
          />
        </n-grid-item>
        <n-grid-item :span="8">
          <AlarmDistribution
            ref="alarmDistributionRef"
            :distributionData="distributionData"
            :loading="chartLoading"
          />
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 告警列表 -->
    <div class="list-section">
      <AlarmList
        ref="alarmListRef"
        :tableData="tableData"
        :loading="tableLoading"
        :pagination="pagination"
        @update="handleTableUpdate"
        @acknowledge="handleAcknowledge"
        @resolve="handleResolve"
        @batch-acknowledge="handleBatchAcknowledge"
        @batch-resolve="handleBatchResolve"
      />
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-bar">
      <n-space>
        <n-button 
          type="success" 
          @click="handleGenerateAlarms" 
          :loading="generateLoading"
        >
          <template #icon>
            <n-icon :component="Alert" />
          </template>
          {{ generateLoading ? "生成中..." : "从异常数据生成告警" }}
        </n-button>
        
        <n-button type="primary" @click="handleExport" :loading="exportLoading">
          <template #icon>
            <n-icon :component="Download" />
          </template>
          {{ exportLoading ? "生成中..." : "导出报表" }}
        </n-button>
      </n-space>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useMessage } from "naive-ui";
import { Download, Alert } from "@vicons/ionicons5";
import AlarmKpiCards from "@/components/alarm/KpiCards.vue";
import AlarmTrend from "@/components/alarm/Trend.vue";
import AlarmDistribution from "@/components/alarm/Distribution.vue";
import AlarmList from "@/components/alarm/List.vue";
import AlarmDetailTable from "@/components/alarm/DetailTable.vue";
import * as alarmApi from "@/api/alarm";
import type {
  AlarmItem,
  AlarmQueryParams,
  AlarmListItem,
  AlarmTypeDict,
  AlarmLevelDict,
} from "@/api/alarm";
import type {
  BuildingEnergyDetailResponse,
  BuildingEnergyDetail,
  EnergySummary,
} from "@/types/analysis";
import { useAppStore } from "@/store/app";

const message = useMessage();
const appStore = useAppStore();

// 状态
const queryLoading = ref(false);
const tableLoading = ref(false);
const metricsLoading = ref(false);
const chartLoading = ref(false);
const exportLoading = ref(false);
const generateLoading = ref(false);

// 查询表单
const queryFormRef = ref<any>(null);

const queryForm = reactive({
  buildings: [] as string[],
  severity: [] as string[],
  alarmType: [] as string[],
  timeRange: null as [number, number] | null,
});

// 验证规则
const queryRules = {
  timeRange: [
    {
      required: true,
      message: "请选择时间范围",
      trigger: ["blur", "change"],
      validator: (rule: any, value: [number, number] | null) => {
        if (!value || !Array.isArray(value) || value.length !== 2) {
          return new Error("请选择时间范围");
        }
        if (!value[0] || !value[1]) {
          return new Error("请选择时间范围");
        }
        return true;
      },
    },
  ],
};

// 建筑选项（从后端获取）
const buildingOptions = ref<any[]>([]);

// 告警级别选项（从后端获取）
const severityOptions = ref<any[]>([]);

// 告警类型选项（从后端获取）
const alarmTypeOptions = ref<any[]>([]);

// 表格数据
const tableData = ref<any[]>([]);
const pagination = reactive({
  page: 1,
  pageSize: 10,
  pageSizes: [10, 20, 50],
  showSizePicker: true,
  onChange: (page: number) => {
    pagination.page = page;
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize;
    pagination.page = 1;
  },
});

// 指标数据
const metrics = ref({
  totalAlarms: 0,
  unresolvedCount: 0,
  criticalCount: 0,
  acknowledgedCount: 0,
});

// 图表数据
const trendData = ref<any[]>([]);
const distributionData = ref<any[]>([]);

// 能耗详情数据
const energyDetailData = ref<BuildingEnergyDetail[]>([]);
const energySummaryData = ref<EnergySummary | undefined>(undefined);
const energyDetailPeriod = ref<string>("");

// 组件引用
const alarmTrendRef = ref<InstanceType<typeof AlarmTrend> | null>(null);
const alarmDistributionRef = ref<InstanceType<typeof AlarmDistribution> | null>(
  null,
);
const alarmListRef = ref<InstanceType<typeof AlarmList> | null>(null);

// 获取建筑列表
const loadBuildings = async () => {
  try {
    const response = await alarmApi.getBuildings();
    const buildings = response.data.data || [];

    buildingOptions.value = buildings.map((building: any) => ({
      label: building.name || `建筑${building.id || building.building_id}`,
      value: building.id || building.building_id,
    }));
  } catch (error: any) {
    console.error("获取建筑列表失败:", error);
  }
};

// 获取告警级别字典
const loadAlarmLevels = async () => {
  try {
    const response = await alarmApi.getAlarmLevels();
    const levels = response.data?.data || [];

    severityOptions.value = levels.map((level: AlarmLevelDict) => ({
      label: level.name,
      value: level.level,
      style: { color: level.color },
    }));
  } catch (error: any) {
    console.error("获取告警级别失败:", error);
  }
};

// 获取告警类型字典
const loadAlarmTypes = async () => {
  try {
    const response = await alarmApi.getAlarmTypes();
    const types = response.data?.data || [];

    alarmTypeOptions.value = types.map((type: AlarmTypeDict) => ({
      label: type.name,
      value: type.code,
    }));
  } catch (error: any) {
    console.error("获取告警类型失败:", error);
  }
};

// 设置快捷时间 - 基于 app store 的方法
const setQuickTime = (type: "today" | "week" | "month") => {
  let start: Date;
  let end: Date;

  switch (type) {
    case "today":
      // 今日
      const todayRange = appStore.getTodayRange();
      start = new Date(todayRange.start);
      end = new Date(todayRange.end);
      break;
    case "week":
      // 本周
      const weekRange = appStore.getWeekRange();
      start = new Date(weekRange.start);
      end = new Date(weekRange.end);
      break;
    case "month":
      // 本月
      const monthRange = appStore.getMonthRange();
      start = new Date(monthRange.start);
      end = new Date(monthRange.end);
      break;
  }

  queryForm.timeRange = [start.getTime(), end.getTime()];

  // 清除验证错误 - 使用 Naive UI 正确的方法
  if (queryFormRef.value) {
    queryFormRef.value.restoreValidation();
  }
};

// 执行查询 - 对接真实接口
const handleQuery = async (skipValidation: boolean = false) => {
  if (!skipValidation) {
    try {
      await queryFormRef.value?.validate();
    } catch (error) {
      message.warning("请填写完整的查询条件");
      return;
    }
  }

  // 确保选择了建筑
  if (!queryForm.buildings || queryForm.buildings.length === 0) {
    message.warning("请选择建筑");
    return;
  }

  queryLoading.value = true;
  tableLoading.value = true;
  metricsLoading.value = true;
  chartLoading.value = true;

  try {
    // 准备查询参数 - 使用全局 Mock 日期
    const startDate = queryForm.timeRange
      ? new Date(queryForm.timeRange[0]).toISOString().split("T")[0]
      : appStore.getMockToday();
    const endDate = queryForm.timeRange
      ? new Date(queryForm.timeRange[1]).toISOString().split("T")[0]
      : appStore.getMockToday();

    // 验证时间范围（2016-07-01 至 2016-09-30）
    const validStartDate = "2016-07-01";
    const validEndDate = "2016-09-30";

    if (
      startDate < validStartDate ||
      endDate > validEndDate
    ) {
      message.error(`查询时间必须在 ${validStartDate} 至 ${validEndDate} 之间`);
      queryLoading.value = false;
      tableLoading.value = false;
      metricsLoading.value = false;
      chartLoading.value = false;
      return;
    }

    // 使用用户选择的第一个建筑 ID（必须是从后端获取的真实 ID）
    const buildingId = queryForm.buildings[0];
    const [alarmRes, summaryRes, trendRes, distributionRes, detailRes] =
      await Promise.all([
        alarmApi.getAlarmList({
          // 使用告警列表接口 - 添加时间参数
          building_id: buildingId,
          start_date: startDate,
          end_date: endDate,
          page: pagination.page,
          page_size: pagination.pageSize,
        }),
        alarmApi.getAlarmSummary({
          // 统计摘要
          building_id: buildingId,
          start_date: startDate,
          end_date: endDate,
          time_unit: "day",
        }),
        alarmApi.getAlarmTrend({
          // 趋势图数据
          building_id: buildingId,
          start_date: startDate,
          end_date: endDate,
        }),
        alarmApi.getAlarmDistribution({
          // 分布图数据 - 告警类型统计（饼图）
          building_id: buildingId,
          start_date: startDate,
          end_date: endDate,
        }),
        // 获取能耗详情数据 - 使用 statistics API
        import("@/api/statistics").then((mod) =>
          mod.getSummary({
            building_id: buildingId,
            start_date: startDate,
            end_date: endDate,
            time_unit: "day",
          }),
        ),
      ]);

    // 填充表格数据 - getAlarmList 返回格式：{ code, message, data: { total, page, page_size, items } }
    const alarmData = alarmRes.data?.data || { total: 0, page: 1, page_size: 10, items: [] };
    const alarms = Array.isArray(alarmData.items) ? alarmData.items : [];
    
    // 填充分布数据
    const distributionDataValue = distributionRes.data?.data || [];
    // 直接赋值，组件会自动识别 { categories, series } 格式
    distributionData.value = distributionDataValue;
    
    tableData.value = alarms.map((item: any, index: number) => {
      // 映射 status 字段
      const mappedStatus = mapStatus(item.status);
      
      const processedItem = {
        id: item.id || item.alarm_id || `alarm_${index}`,
        // 使用 start_time 作为告警时间
        time: item.start_time || item.timestamp || item.time,
        building_id: item.building_id,
        building_name:
          item.building_name || getBuildingName(item.building_id),
        alarm_type: item.alarm_type,
        // 注意：severity 是字符串类型，用于表格显示
        severity: item.severity || String(item.alarm_level),
        status: mappedStatus,
        description: item.description,
        buildingName: item.building_name || getBuildingName(item.building_id),
        alarmTypeName: getAlarmTypeName(item.alarm_type),
        severityName: getSeverityName(
          item.severity || String(item.alarm_level),
        ),
        end_time: item.end_time,
        value: item.value,
        threshold: item.threshold,
        meter_id: item.meter_id,
        solution: item.solution,
        // 保留 alarm_level 用于 KPI 计算
        alarm_level: item.alarm_level,
      };
      
      return processedItem;
    });
    
    const summaryData = summaryRes.data.data?.summary || {};
    metrics.value = {
      totalAlarms:
        summaryData?.total_alarm_count || alarmData.total || alarms.length,
      unresolvedCount:
        summaryData?.unresolved_count ||
        alarms.filter((a) => a.status === "unresolved").length,
      criticalCount:
        summaryData?.critical_count || 0, // queryAlarms 接口没有返回 alarm_level
      acknowledgedCount:
        summaryData?.acknowledged_count ||
        alarms.filter((a) => a.status === "acknowledged").length,
    };
    
    // 图表数据 - 后端返回的是 { categories, series } 格式
    trendData.value = trendRes.data.data || { categories: [], series: [] };
    distributionData.value = distributionRes.data.data || {
      categories: [],
      series: [],
    };
    
    // 填充能耗详情数据
    if (detailRes && detailRes.data?.data) {
      const detailData = detailRes.data.data;
      energyDetailData.value = detailData.details || [];
      energySummaryData.value = detailData.summary || undefined;
      energyDetailPeriod.value =
        detailData.period || `${startDate} 至 ${endDate}`;
    } else {
      energyDetailData.value = [];
      energySummaryData.value = undefined;
      energyDetailPeriod.value = "";
    }

    // 更新图表
    if (alarmTrendRef.value) {
      alarmTrendRef.value.updateChart(trendData.value);
    }
    
    if (alarmDistributionRef.value) {
      alarmDistributionRef.value.updateChart(distributionData.value);
    }

    message.success("查询成功");
  } catch (error: any) {
    console.error("查询失败:", error);
    message.error("查询失败：" + (error.message || "未知错误"));
  } finally {
    queryLoading.value = false;
    tableLoading.value = false;
    metricsLoading.value = false;
    chartLoading.value = false;
  }
};

// 重置查询
const handleReset = () => {
  queryForm.buildings = [];
  queryForm.severity = [];
  queryForm.alarmType = [];
  queryForm.timeRange = null;
  tableData.value = [];
  metrics.value = {
    totalAlarms: 0,
    unresolvedCount: 0,
    criticalCount: 0,
    acknowledgedCount: 0,
  };
  trendData.value = [];
  distributionData.value = [];

  if (alarmTrendRef.value) {
    alarmTrendRef.value.clearChart();
  }
  if (alarmDistributionRef.value) {
    alarmDistributionRef.value.clearChart();
  }

  message.success("已重置");
};

// 表格更新回调
const handleTableUpdate = (page: number, pageSize: number) => {
  pagination.page = page;
  pagination.pageSize = pageSize;
  handleQuery();
};

// 获取告警类型名称
const getAlarmTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    energy_anomaly: "能耗异常",
    device_fault: "设备故障",
    sensor_error: "传感器异常",
    communication_error: "通信故障",
    threshold_exceeded: "超限告警",
    equipment: "设备告警",
    energy: "能耗告警",
    environment: "环境告警",
  };
  return typeMap[type] || type;
};

// 获取级别名称
const getSeverityName = (severity: string) => {
  const severityMap: Record<string, string> = {
    critical: "紧急",
    major: "重要",
    minor: "一般",
    warning: "提示",
    "1": "严重",
    "2": "警告",
    "3": "提示",
  };
  return severityMap[severity] || severity;
};

// 获取建筑名称（辅助函数）
const getBuildingName = (buildingId: string) => {
  const building = buildingOptions.value.find((b) => b.value === buildingId);
  return building?.label || buildingId;
};

// 映射后端状态到前端状态
const mapStatus = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: "unresolved",
    confirmed: "acknowledged",
    resolved: "resolved",
  };
  return statusMap[status] || status;
};

// 确认告警 - 对接真实接口
const handleAcknowledge = async (alarmId: string) => {
  try {
    // 使用新接口的单个确认（通过批量接口实现）
    await alarmApi.batchConfirmAlarms({
      alarm_ids: [parseInt(alarmId) || 0],
    });
    message.success("告警已确认");
    handleQuery(true); // 跳过验证，直接刷新列表和 metrics 指标
  } catch (error: any) {
    console.error("确认失败:", error);
    message.error("确认失败：" + (error.message || "未知错误"));
  }
};

// 解决告警 - 对接真实接口
const handleResolve = async (alarmId: string) => {
  try {
    // 使用新接口的单个解决（通过批量接口实现）
    await alarmApi.batchResolveAlarms({
      alarm_ids: [parseInt(alarmId) || 0],
    });
    message.success("告警已解决");
    handleQuery(true); // 跳过验证，直接刷新列表和 metrics 指标
  } catch (error: any) {
    console.error("解决失败:", error);
    message.error("解决失败：" + (error.message || "未知错误"));
  }
};

// 批量确认告警 - 新增
const handleBatchAcknowledge = async (alarmIds: string[]) => {
  try {
    const ids = alarmIds
      .map((id) => parseInt(id) || 0)
      .filter((id) => id !== 0);

    if (ids.length === 0) {
      message.warning("没有有效的告警 ID");
      return;
    }

    const response = await alarmApi.batchConfirmAlarms({
      alarm_ids: ids,
    });

    const result = response.data?.data;
    const successCount = result?.confirmed_count || 0;
    const failedCount = result?.failed_ids?.length || 0;

    if (successCount > 0) {
      message.success(`成功确认 ${successCount} 条告警`);
    }

    if (failedCount > 0) {
      message.warning(`${failedCount} 条告警无法确认（可能已处理）`);
    }

    handleQuery(true); // 跳过验证，直接刷新列表和 metrics 指标
  } catch (error: any) {
    console.error("批量确认失败:", error);
    message.error("批量确认失败：" + (error.message || "未知错误"));
  }
};

// 批量解决告警 - 新增
const handleBatchResolve = async (alarmIds: string[]) => {
  try {
    const ids = alarmIds
      .map((id) => parseInt(id) || 0)
      .filter((id) => id !== 0);

    if (ids.length === 0) {
      message.warning("没有有效的告警 ID");
      return;
    }

    const response = await alarmApi.batchResolveAlarms({
      alarm_ids: ids,
    });

    const result = response.data?.data;
    const successCount = result?.resolved_count || 0;
    const failedCount = result?.failed_ids?.length || 0;

    if (successCount > 0) {
      message.success(`成功解决 ${successCount} 条告警`);
    }

    if (failedCount > 0) {
      message.warning(`${failedCount} 条告警无法解决（可能已解决）`);
    }

    handleQuery(true); // 跳过验证，直接刷新列表和 metrics 指标
  } catch (error: any) {
    console.error("批量解决失败:", error);
    message.error("批量解决失败：" + (error.message || "未知错误"));
  }
};

// 从异常数据生成告警（使用真实算法）
const handleGenerateAlarms = async () => {
  // 确保选择了建筑
  if (!queryForm.buildings || queryForm.buildings.length === 0) {
    message.warning("请选择建筑");
    return;
  }
  
  generateLoading.value = true;
  
  try {
    // 准备查询参数
    const startDate = queryForm.timeRange
      ? new Date(queryForm.timeRange[0]).toISOString().split("T")[0]
      : appStore.getMockToday();
    const endDate = queryForm.timeRange
      ? new Date(queryForm.timeRange[1]).toISOString().split("T")[0]
      : appStore.getMockToday();
    
    // 验证时间范围（2016-07-01 至 2016-09-30）
    const validStartDate = "2016-07-01";
    const validEndDate = "2016-09-30";
    
    if (
      startDate < validStartDate ||
      startDate > validEndDate ||
      endDate < validStartDate ||
      endDate > validEndDate
    ) {
      message.error(`生成时间必须在 ${validStartDate} 至 ${validEndDate} 之间`);
      generateLoading.value = false;
      return;
    }
    
    // 调用新接口 - 使用真实检测算法
    const response = await alarmApi.generateRealAlarms({
      start_date: startDate,
      end_date: endDate,
      building_ids: queryForm.buildings.join(','), // 逗号分隔的建筑 ID 列表
      metric: 'electricity', // 默认检测用电量
      dynamic_window: 24, // 24 小时窗口
      dynamic_threshold: 2.5, // 2.5 倍标准差
      trend_window: 6, // 6 个点趋势检测
      min_trend_decline: 0.15 // 最小下降 15%
    });
    
    const generatedCount = response.data?.data?.generated_count || 0;
    
    if (generatedCount > 0) {
      const severityDist = response.data?.data?.severity_distribution || {};
      const methodDist = response.data?.data?.method_distribution || {};
      
      let messageDetail = `成功生成 ${generatedCount} 条真实告警\n`;
      messageDetail += `动态基线：${methodDist.dynamic_baseline || 0} 条\n`;
      messageDetail += `趋势下降：${methodDist.trend_decline || 0} 条\n`;
      if (severityDist.critical > 0) messageDetail += `严重：${severityDist.critical} 条 `;
      if (severityDist.high > 0) messageDetail += `警告：${severityDist.high} 条 `;
      if (severityDist.medium > 0) messageDetail += `中等：${severityDist.medium} 条 `;
      if (severityDist.low > 0) messageDetail += `提示：${severityDist.low} 条`;
      
      message.success(messageDetail);
      
      // 生成成功后自动刷新当前查询结果
      handleQuery(true);
    } else {
      message.warning("没有检测到异常数据，无法生成告警");
    }
  } catch (error: any) {
    console.error("生成告警失败:", error);
    message.error("生成告警失败：" + (error.message || "未知错误"));
  } finally {
    generateLoading.value = false;
  }
};

// 导出报表 - 对接真实接口
const handleExport = async () => {
  exportLoading.value = true;
  message.info("正在生成报表...");

  try {
    const startDate = queryForm.timeRange
      ? new Date(queryForm.timeRange[0]).toISOString().split("T")[0]
      : new Date().toISOString().split("T")[0];
    const endDate = queryForm.timeRange
      ? new Date(queryForm.timeRange[1]).toISOString().split("T")[0]
      : new Date().toISOString().split("T")[0];

    // 验证时间范围（2016-07-01 至 2016-09-30）
    const validStartDate = "2016-07-01";
    const validEndDate = "2016-09-30";

    if (
      startDate < validStartDate ||
      startDate > validEndDate ||
      endDate < validStartDate ||
      endDate > validEndDate
    ) {
      message.error(`导出时间必须在 ${validStartDate} 至 ${validEndDate} 之间`);
      exportLoading.value = false;
      return;
    }

    // 确保使用从后端获取的真实建筑 ID
    if (!queryForm.buildings || queryForm.buildings.length === 0) {
      message.warning("请选择建筑");
      exportLoading.value = false;
      return;
    }

    const exportParams = {
      building_ids: queryForm.buildings,
      startTime: startDate,
      endTime: endDate,
      format: "excel" as const,
    };

    const response = await alarmApi.exportExcel(exportParams);

    const url = window.URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `告警报表_${startDate}_${endDate}_${Date.now()}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    message.success("报表已下载");
  } catch (error: any) {
    console.error("导出失败:", error);
    message.error("导出失败：" + (error.message || "未知错误"));
  } finally {
    exportLoading.value = false;
  }
};

onMounted(async () => {
  // 初始化时执行查询
  await loadBuildings();
  loadAlarmLevels();
  loadAlarmTypes();
  if (buildingOptions.value.length > 0) {
    queryForm.buildings = [buildingOptions.value[0].value];
    setQuickTime("week"); // 默认查询近一周
    handleQuery();
  }
});
</script>

<style scoped>
.alarm-container {
  padding: 16px;
  background-color: var(--bg-color);
  min-height: 100vh;
}

.query-section {
  margin-bottom: 16px;
}

.metrics-section {
  margin-bottom: 16px;
}

.charts-section {
  margin-bottom: 16px;
}

.list-section {
  margin-bottom: 16px;
}

.detail-section {
  margin-bottom: 16px;
}

.bottom-bar {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}
</style>
