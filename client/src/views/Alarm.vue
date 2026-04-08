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
        :resolvingAlarmIds="resolvingAlarmIds"
        @update="handleTableUpdate"
        @acknowledge="handleAcknowledge"
        @resolve="handleResolve"
        @batch-acknowledge="handleBatchAcknowledge"
        @batch-resolve="handleBatchResolve"
      />
    </div>

    <n-modal
      v-model:show="showResolveModal"
      preset="card"
      title="填写解决办法"
      style="width: 560px"
      :mask-closable="!resolveSubmitting"
      :closable="!resolveSubmitting"
    >
      <n-space vertical :size="12">
        <div class="resolve-modal-hint">
          将解决 {{ resolveForm.alarmIds.length }} 条告警。填写的解决办法会写回告警记录，并在解决后沉淀到知识库。
        </div>
        <n-input
          v-model:value="resolveForm.resolution"
          type="textarea"
          placeholder="请输入排查过程、处理措施和最终结论"
          :rows="6"
          maxlength="1000"
          show-count
        />
      </n-space>
      <template #footer>
        <n-space justify="end">
          <n-button @click="closeResolveModal" :disabled="resolveSubmitting">
            取消
          </n-button>
          <n-button
            type="success"
            @click="submitResolve"
            :loading="resolveSubmitting"
          >
            确认解决并入库
          </n-button>
        </n-space>
      </template>
    </n-modal>

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
import { ref, reactive, onMounted, nextTick } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useMessage } from "naive-ui";
import { Download,Alert } from "@vicons/ionicons5";
import AlarmKpiCards from "@/components/alarm/KpiCards.vue";
import AlarmTrend from "@/components/alarm/Trend.vue";
import AlarmDistribution from "@/components/alarm/Distribution.vue";
import AlarmList from "@/components/alarm/List.vue";
import * as alarmApi from "@/api/alarm";
import type {
  AlarmTypeDict,
  AlarmLevelDict,
} from "@/api/alarm";
import type {
  BuildingEnergyDetail,
  EnergySummary,
} from "@/types/analysis";
import { useAppStore } from "@/store/app";
import { useBuildingStore } from "@/store/building";

const message = useMessage();
const appStore = useAppStore();
const buildingStore = useBuildingStore();
const route = useRoute();

// 状态
const queryLoading = ref(false);
const tableLoading = ref(false);
const metricsLoading = ref(false);
const chartLoading = ref(false);
const exportLoading = ref(false);
const generateLoading = ref(false);
const showResolveModal = ref(false);
const resolveSubmitting = ref(false);
const resolvingAlarmIds = ref<string[]>([]);

// 查询表单
const queryFormRef = ref<any>(null);

const queryForm = reactive({
  buildings: [] as string[],
  severity: [] as string[],
  alarmType: [] as string[],
  timeRange: null as [number, number] | null,
});

const resolveForm = reactive({
  alarmIds: [] as number[],
  resolution: "",
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
const trendData = ref<any>({ categories: [], series: [] });
const distributionData = ref<any>({ categories: [], series: [] });

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

// 获取建筑列表（从 store 获取固定数据）
const loadBuildings = () => {
  try {
    const buildings = buildingStore.buildings || [];

    buildingOptions.value = buildings.map((building: any) => ({
      label: building.name || `建筑${building.id || building.building_id}`,
      value: building.id || building.building_id,
    }));
  } catch (error: any) {
    // 静默处理错误
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
    // 静默处理错误
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
    // 静默处理错误
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

    // 支持多建筑查询 - 循环调用 API 并合并结果
    const allAlarms: any[] = [];
    const allTrendData: any[] = [];
    const allDistributionData: any[] = [];

    // 为每个建筑获取数据
    for (const buildingId of queryForm.buildings) {
      const [alarmRes, trendRes, distributionRes] = await Promise.all([
        alarmApi.getAlarmList({
          // 使用告警列表接口 - 添加时间参数
          building_id: buildingId,
          start_date: startDate,
          end_date: endDate,
          page: pagination.page,
          page_size: pagination.pageSize,
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
      ]);

      // 收集告警列表
      const alarmData = alarmRes.data?.data || { total: 0, page: 1, page_size: 10, items: [] };
      const alarms = Array.isArray(alarmData.items) ? alarmData.items : [];
      allAlarms.push(...alarms);

      // 收集趋势数据
      const trendResData = trendRes.data?.data || { categories: [], series: [] };
      if (trendResData.series && trendResData.series.length > 0) {
        allTrendData.push(trendResData);
      }

      // 收集分布数据
      const distributionResData = distributionRes.data?.data || { categories: [], series: [] };
      if (distributionResData.series && distributionResData.series.length > 0) {
        allDistributionData.push(distributionResData);
      }
    }

    // 填充表格数据 - 映射所有建筑的告警数据
    tableData.value = allAlarms.map((item: any, index: number) => {
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
    
    // 基于告警列表计算所有 KPI 指标
    const totalAlarms = allAlarms.length;
    // 未解决：pending 和 confirmed 状态
    const unresolvedCount = allAlarms.filter((a) => 
      a.status === "pending" || a.status === "confirmed"
    ).length;
    // 已确认：acknowledged 和 resolved 状态
    const acknowledgedCount = allAlarms.filter((a) => 
      a.status === "acknowledged" || a.status === "resolved"
    ).length;
    // 紧急告警：alarm_level <= 2（严重和警告）
    const criticalCount = allAlarms.filter((a) => {
      const level = a.alarm_level || parseInt(a.severity) || 0;
      return level <= 2;
    }).length;
    
    metrics.value = {
      totalAlarms,
      unresolvedCount,
      criticalCount,
      acknowledgedCount,
    };
    
    // 合并图表数据 - 支持多建筑数据聚合
    trendData.value = mergeTrendData(allTrendData);
    distributionData.value = mergeDistributionData(allDistributionData);

    // 更新图表
    if (alarmTrendRef.value) {
      alarmTrendRef.value.updateChart(trendData.value);
    }
    
    if (alarmDistributionRef.value) {
      alarmDistributionRef.value.updateChart(distributionData.value);
    }

    message.success("查询成功");
  } catch (error: any) {
    message.error("查询失败：" + (error.message || "未知错误"));
  } finally {
    queryLoading.value = false;
    tableLoading.value = false;
    metricsLoading.value = false;
    chartLoading.value = false;
  }
};

// 合并趋势图数据 - 多建筑数据聚合
const mergeTrendData = (trendDataArray: any[]) => {
  if (!trendDataArray || trendDataArray.length === 0) {
    return { categories: [], series: [] };
  }
  
  // 如果只有一个建筑，直接返回
  if (trendDataArray.length === 1) {
    return trendDataArray[0];
  }
  
  // 合并多个建筑的趋势数据
  const categorySet = new Set<string>();
  const seriesMap = new Map<string, number[]>();
  
  // 收集所有时间点和对应的数值
  trendDataArray.forEach((data) => {
    if (!data.categories || !data.series) return;
    
    // 添加时间点
    data.categories.forEach((category: string) => categorySet.add(category));
    
    // 合并每个系列的数据
    data.series.forEach((serie: any) => {
      const seriesName = serie.name || '告警数';
      if (!seriesMap.has(seriesName)) {
        seriesMap.set(seriesName, []);
      }
      
      // 累加对应时间点的值
      const existingValues = seriesMap.get(seriesName)!;
      serie.data.forEach((value: number, index: number) => {
        if (existingValues[index] === undefined) {
          existingValues[index] = 0;
        }
        existingValues[index] += value || 0;
      });
    });
  });
  
  // 转换为 ECharts 格式
  const categories = Array.from(categorySet);
  const series = Array.from(seriesMap.entries()).map(([name, data]) => ({
    name,
    type: 'line',
    data,
  }));
  
  return { categories, series };
};

// 合并分布图数据 - 多建筑数据聚合（饼图/柱状图）
const mergeDistributionData = (distributionDataArray: any[]) => {
  if (!distributionDataArray || distributionDataArray.length === 0) {
    return { categories: [], series: [] };
  }
  
  // 如果只有一个建筑，直接返回
  if (distributionDataArray.length === 1) {
    return distributionDataArray[0];
  }
  
  // 合并多个建筑的分布数据
  const categoryMap = new Map<string, number>();
  
  distributionDataArray.forEach((data) => {
    if (!data.categories || !data.series) return;
    
    // 遍历每个类别并累加数值
    data.categories.forEach((category: string, index: number) => {
      const currentValue = categoryMap.get(category) || 0;
      const seriesValue = data.series[0]?.data?.[index] || 0;
      categoryMap.set(category, currentValue + seriesValue);
    });
  });
  
  // 转换为 ECharts 格式
  const categories = Array.from(categoryMap.keys());
  const values = Array.from(categoryMap.values());
  const series = [{
    name: '告警分布',
    type: 'pie',
    data: categories.map((category, index) => ({
      name: category,
      value: values[index],
    })),
  }];
  
  return { categories, series };
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
    message.error("确认失败：" + (error.message || "未知错误"));
  }
};

const resetResolveModal = () => {
  showResolveModal.value = false;
  resolveForm.alarmIds = [];
  resolveForm.resolution = "";
};

const closeResolveModal = () => {
  if (resolveSubmitting.value) {
    return;
  }

  resetResolveModal();
};

const appendResolvingAlarmIds = (alarmIds: string[]) => {
  const merged = new Set([
    ...resolvingAlarmIds.value,
    ...alarmIds.map((id) => String(id)),
  ]);
  resolvingAlarmIds.value = Array.from(merged);
};

const removeResolvingAlarmIds = (alarmIds: string[]) => {
  const pending = new Set(alarmIds.map((id) => String(id)));
  resolvingAlarmIds.value = resolvingAlarmIds.value.filter(
    (id) => !pending.has(String(id)),
  );
};

const openResolveModal = (alarmIds: string[]) => {
  const ids = alarmIds
    .map((id) => parseInt(id) || 0)
    .filter((id) => id !== 0);
  const pendingIds = ids.filter(
    (id) => !resolvingAlarmIds.value.includes(String(id)),
  );

  if (pendingIds.length === 0) {
    message.warning("所选告警正在后台处理中");
    return;
  }

  resolveForm.alarmIds = pendingIds;
  resolveForm.resolution = "";
  showResolveModal.value = true;
};

const resolveInBackground = async (alarmIds: string[], resolution: string) => {
  try {
    const response = await alarmApi.batchResolveAlarms({
      alarm_ids: alarmIds.map((id) => parseInt(id) || 0),
      resolution,
    });

    const result = response.data?.data;
    const successCount = result?.resolved_count || 0;
    const failedCount = result?.failed_ids?.length || 0;
    const knowledgeSyncedCount = result?.knowledge_synced_count || 0;

    if (successCount > 0) {
      const knowledgeText =
        knowledgeSyncedCount > 0 ? `，已沉淀 ${knowledgeSyncedCount} 条知识` : "";
      message.success(`成功解决 ${successCount} 条告警${knowledgeText}`);
    }

    if (failedCount > 0) {
      message.warning(`${failedCount} 条告警无法解决（可能已解决）`);
    }

    await handleQuery(true);
  } catch (error: any) {
    message.error(
      "解决失败：" +
        (error.response?.data?.message || error.message || "未知错误"),
    );
  } finally {
    removeResolvingAlarmIds(alarmIds);
  }
};

const submitResolve = async () => {
  const resolution = resolveForm.resolution.trim();

  if (resolveForm.alarmIds.length === 0) {
    message.warning("没有可解决的告警");
    closeResolveModal();
    return;
  }

  if (!resolution) {
    message.warning("请先填写解决办法");
    return;
  }

  try {
    resolveSubmitting.value = true;
    const alarmIds = resolveForm.alarmIds.map((id) => String(id));

    appendResolvingAlarmIds(alarmIds);
    resetResolveModal();
    resolveSubmitting.value = false;
    message.info("已提交解决请求，后台处理中");

    void resolveInBackground(alarmIds, resolution);
  } catch (error: any) {
    resolveSubmitting.value = false;
    message.error(
      "解决失败：" +
        (error.response?.data?.message || error.message || "未知错误"),
    );
  }
};

// 解决告警 - 打开解决弹窗
const handleResolve = (alarmId: string) => {
  openResolveModal([alarmId]);
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
    message.error("批量确认失败：" + (error.message || "未知错误"));
  }
};

// 批量解决告警 - 打开统一解决弹窗
const handleBatchResolve = (alarmIds: string[]) => {
  openResolveModal(alarmIds);
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

    const response = await alarmApi.exportExcel(exportParams)

    // exportExcel 返回的是 AxiosResponse，需要提取 data 中的 Blob
    const blob = response.data

    const url = window.URL.createObjectURL(blob as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `告警报表_${startDate}_${endDate}_${Date.now()}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    message.success("报表已下载");
  } catch (error: any) {
    message.error("导出失败：" + (error.message || "未知错误"));
  } finally {
    exportLoading.value = false;
  }
};

// 页面加载时
onMounted(async () => {
  // 1. 先加载建筑列表和字典数据
  await Promise.all([
    loadBuildings(),
    loadAlarmLevels(),
    loadAlarmTypes()
  ])
  
  // 2. 检测路由参数，判断是否需要高亮特定告警
  const highlightId = route.query.highlight_id as string
  const expandDetail = route.query.expand_detail === 'true'
  const buildingId = route.query.building_id as string
  const alarmTime = route.query.alarm_time as string
  
  if (highlightId && buildingId) {
    // 设置查询条件为告警所在建筑
    queryForm.buildings = [buildingId]
    
    // 根据告警时间设置时间范围（告警时间前后 7 天）
    if (alarmTime) {
      const alarmDate = new Date(alarmTime)
      const startDate = new Date(alarmDate)
      startDate.setDate(alarmDate.getDate() - 7)
      const endDate = new Date(alarmDate)
      endDate.setDate(alarmDate.getDate() + 7)
      
      queryForm.timeRange = [startDate.getTime(), endDate.getTime()]
    } else {
      // 如果没有告警时间，默认使用近 7 天
      setQuickTime('week')
    }
    
    // 查询告警列表
    await handleQuery()
    
    // 等待列表加载完成后，高亮并展开指定告警
    await nextTick()
    
    if (expandDetail && alarmListRef.value) {
      // 找到对应的告警行 - 优先匹配 highlight_id，同时兼容时间和建筑匹配
      const alarmRow = tableData.value.find(
        (item: any) => {
          // 优先匹配 ID（支持数字和字符串比较）
          if (String(item.id) === String(highlightId)) return true
          // 如果 ID 不匹配，尝试匹配时间和建筑（防止 ID 格式不一致）
          if (alarmTime && item.building_id === buildingId) {
            const itemTime = new Date(item.time).getTime()
            const targetTime = new Date(alarmTime).getTime()
            // 时间相差不超过 1 小时
            return Math.abs(itemTime - targetTime) < 3600000
          }
          return false
        }
      )
      
      if (alarmRow) {
        message.success('已定位到指定告警')
        
        // 使用 setTimeout 延迟执行，确保 DOM 完全渲染
        setTimeout(async () => {
          // 调用子组件的查看详情方法
          ;(alarmListRef.value as any).handleViewDetail(alarmRow)
          
          // 等待弹窗完全打开
          await nextTick()
          await nextTick()
        }, 300) // 延迟 300ms 执行
      } else {
        message.warning('未找到指定的告警，请检查筛选条件')
      }
    }
  } else {
    // 没有高亮参数，执行正常初始化
    if (buildingOptions.value.length > 0) {
      queryForm.buildings = [buildingOptions.value[0].value]
      setQuickTime('week') // 默认查询近一周
      handleQuery()
    }
  }
})
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

.resolve-modal-hint {
  color: var(--n-text-color-2);
  line-height: 1.7;
}

.bottom-bar {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}
</style>
