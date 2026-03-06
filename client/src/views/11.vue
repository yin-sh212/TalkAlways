<template>
  <div class="dashboard-container">
    <el-collapse v-model="activeNames" class="filter-card">
      <el-collapse-item title="查询条件控制台" name="1">
        <el-form :inline="true" :model="queryParams" class="filter-form">
          <el-form-item label="建筑选择">
            <el-select 
              v-model="queryParams.buildings" 
              multiple 
              filterable 
              placeholder="搜索建筑名称"
              style="width: 300px"
            >
              <el-option label="A 栋教学楼" value="A" />
              <el-option label="B 栋实验楼" value="B" />
              <el-option label="C 栋办公楼" value="C" />
              <el-option label="D 栋宿舍楼" value="D" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="参数选择">
            <el-select v-model="queryParams.parameter" style="width: 150px">
              <el-option label="电力能耗" value="electricity" />
              <el-option label="空调能耗" value="ac" />
              <el-option label="环境温度" value="temp" />
              <el-option label="COP 值" value="cop" />
            </el-select>
          </el-form-item>

          <el-form-item label="时间范围">
            <el-date-picker
              v-model="queryParams.dateRange"
              type="daterange"
              unlink-panels
              :shortcuts="shortcuts"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              style="width: 240px"
            />
          </el-form-item>

          <el-form-item class="nl-input-item">
            <el-input
              v-model="nlQuery"
              placeholder="试试说：A 栋上周每天的空调电耗"
              style="width: 320px"
              @keyup.enter="handleSearch"
              clearable
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleSearch" :loading="loading">
              <el-icon><Search /></el-icon>
              查询
            </el-button>
            <el-button @click="resetQuery">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-collapse-item>
    </el-collapse>

    <el-tabs v-model="activeTab" class="result-tabs">
      <el-tab-pane label="分析视图" name="analysis">
        <el-row :gutter="20">
          <el-col :span="18">
            <el-card shadow="hover" class="chart-card">
              <template #header>
                <div class="card-header">
                  <span>能耗趋势折线图</span>
                  <el-icon class="zoom-icon" @click="zoomChart('line')"><FullScreen /></el-icon>
                </div>
              </template>
              <div ref="lineChartRef" style="height: 350px;"></div>
            </el-card>
            <el-card shadow="hover" class="chart-card mt-4">
              <template #header>
                <div class="card-header">
                  <span>能耗分布柱状图</span>
                  <el-icon class="zoom-icon" @click="zoomChart('bar')"><FullScreen /></el-icon>
                </div>
              </template>
              <div ref="barChartRef" style="height: 350px;"></div>
            </el-card>
          </el-col>
          
          <el-col :span="6">
            <el-card shadow="hover" class="statistic-card">
              <el-statistic title="查询时段总能耗" :value="totalEnergy" :precision="2">
                <template #suffix>kWh</template>
              </el-statistic>
            </el-card>
            <el-card shadow="hover" class="statistic-card mt-4">
              <el-statistic title="平均能耗" :value="averageEnergy" :precision="2">
                <template #suffix>kWh</template>
              </el-statistic>
            </el-card>
            <el-card shadow="hover" class="statistic-card mt-4">
              <el-statistic title="异常点数" :value="anomalyCount" value-style="color: #cf1322">
                <template #suffix>个</template>
              </el-statistic>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="数据表格" name="data">
        <el-table 
          :data="tableData" 
          border 
          stripe 
          v-if="tableData.length > 0"
          :page-size="pageSize"
          @sort-change="handleSortChange"
        >
          <el-table-column prop="date" label="时间" sortable="custom" width="120" />
          <el-table-column prop="building" label="建筑" width="120" />
          <el-table-column prop="parameter" label="参数" width="100">
            <template #default="scope">
              <el-tag size="small">{{ getParameterLabel(scope.row.parameter) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="数值" sortable="custom" width="120">
            <template #default="scope">
              {{ scope.row.value?.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="isAnomaly" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row?.isAnomaly ? 'danger' : 'success'" size="small">
                {{ scope.row?.isAnomaly ? '异常' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
        </el-table>
        <el-empty v-else description="暂无数据" />
        
        <div class="pagination-container" v-if="tableData.length > 0">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="totalData"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <div class="footer-bar">
      <el-button type="success" size="large" @click="exportReport" :loading="exporting">
        <el-icon><Download /></el-icon>
        导出报表
      </el-button>
    </div>

    <!-- 图表放大弹窗 -->
    <el-dialog v-model="dialogVisible" title="图表详情" width="90%" :fullscreen="isFullscreen">
      <div ref="zoomChartRef" style="height: 600px;"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import * as echarts from 'echarts';
import { Search, FullScreen, RefreshLeft, Download } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const activeNames = ref(['1']);
const activeTab = ref('analysis');
const nlQuery = ref('');
const exporting = ref(false);
const loading = ref(false);
const lineChartRef = ref(null);
const barChartRef = ref(null);
const zoomChartRef = ref(null);
const tableData = ref([]);
const currentPage = ref(1);
const pageSize = ref(10);
const totalData = ref(0);
const dialogVisible = ref(false);
const isFullscreen = ref(false);
const currentChartType = ref('line');

const queryParams = reactive({
  buildings: [],
  parameter: 'electricity',
  dateRange: []
});

// 快捷日期定义
const shortcuts = [
  { 
    text: '今日', 
    value: () => [new Date(), new Date()] 
  },
  { 
    text: '本周', 
    value: () => {
      const now = new Date();
      const day = now.getDay();
      const diff = now.getDate() - day + (day === 0 ? -6 : 1);
      const monday = new Date(now.setDate(diff));
      return [monday, now];
    } 
  },
  { 
    text: '本月', 
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return [start, now];
    } 
  },
];

// 计算属性
const totalEnergy = computed(() => {
  if (tableData.value.length === 0) return 0;
  return tableData.value.reduce((sum, item) => sum + item.value, 0);
});

const averageEnergy = computed(() => {
  if (tableData.value.length === 0) return 0;
  return totalEnergy.value / tableData.value.length;
});

const anomalyCount = computed(() => {
  return tableData.value.filter(item => item.isAnomaly).length;
});

// 参数标签映射
const getParameterLabel = (param) => {
  const map = {
    'electricity': '电力能耗',
    'ac': '空调能耗',
    'temp': '环境温度',
    'cop': 'COP 值'
  };
  return map[param] || param;
};

// 处理查询（含 NL2Query 逻辑）
const handleSearch = async () => {
  loading.value = true;
  try {
    if (nlQuery.value) {
      // 模拟调用 NL2Query 解析接口
      const parsed = await mockNL2QueryAPI(nlQuery.value);
      // 回填表单
      queryParams.buildings = parsed.buildings;
      queryParams.parameter = parsed.parameter;
      queryParams.dateRange = parsed.dateRange;
      ElMessage.success('已自动解析自然语言条件');
    }
    
    // 模拟数据查询延迟
    await new Promise(resolve => setTimeout(resolve, 500));
    
    updateTableData();
    updateCharts();
    ElMessage.success('查询成功');
  } catch (error) {
    ElMessage.error('查询失败：' + error.message);
  } finally {
    loading.value = false;
  }
};

// 重置查询
const resetQuery = () => {
  queryParams.buildings = [];
  queryParams.parameter = 'electricity';
  queryParams.dateRange = [];
  nlQuery.value = '';
  tableData.value = [];
  totalData.value = 0;
  ElMessage.info('已重置查询条件');
};

// 更新表格数据
const updateTableData = () => {
  // 模拟后端返回的数据
  const mockData = [
    { date: '2024-03-01', building: 'A 栋', parameter: 'electricity', value: 120.5, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-02', building: 'A 栋', parameter: 'electricity', value: 132.3, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-03', building: 'A 栋', parameter: 'electricity', value: 101.8, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-04', building: 'A 栋', parameter: 'electricity', value: 450.2, unit: 'kWh', isAnomaly: true, remark: '周末异常高能耗' },
    { date: '2024-03-05', building: 'A 栋', parameter: 'electricity', value: 134.1, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-06', building: 'B 栋', parameter: 'electricity', value: 90.6, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-07', building: 'B 栋', parameter: 'electricity', value: 230.4, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-08', building: 'A 栋', parameter: 'electricity', value: 145.7, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-09', building: 'A 栋', parameter: 'electricity', value: 158.9, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-10', building: 'A 栋', parameter: 'electricity', value: 167.2, unit: 'kWh', isAnomaly: false, remark: '' },
    { date: '2024-03-11', building: 'B 栋', parameter: 'electricity', value: 520.1, unit: 'kWh', isAnomaly: true, remark: '设备故障导致异常' },
    { date: '2024-03-12', building: 'B 栋', parameter: 'electricity', value: 112.3, unit: 'kWh', isAnomaly: false, remark: '' },
  ];
  
  tableData.value = mockData;
  totalData.value = mockData.length;
};

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val;
};

const handleCurrentChange = (val) => {
  currentPage.value = val;
};

// 排序处理
const handleSortChange = ({ prop, order }) => {
  if (order === 'ascending') {
    tableData.value.sort((a, b) => a[prop] - b[prop]);
  } else if (order === 'descending') {
    tableData.value.sort((a, b) => b[prop] - a[prop]);
  }
};

// 更新图表
const updateCharts = () => {
  updateLineChart();
  updateBarChart();
};

// 更新折线图
const updateLineChart = () => {
  if (!lineChartRef.value) return;
  
  const chart = echarts.getInstanceByDom(lineChartRef.value) || echarts.init(lineChartRef.value);
  
  // 准备数据
  const dates = [...new Set(tableData.value.map(item => item.date))];
  const seriesData = dates.map(date => {
    const item = tableData.value.find(d => d.date === date);
    if (item?.isAnomaly) {
      return {
        value: item.value,
        itemStyle: { color: '#ff4d4f' },
        symbolSize: 10
      };
    }
    return item?.value || 0;
  });
  
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0];
        const dataItem = tableData.value.find(d => d.date === param.name);
        let result = `${param.name}<br/>`;
        result += `能耗：${param.value} kWh<br/>`;
        if (dataItem?.isAnomaly) {
          result += '<span style="color: #ff4d4f">⚠ 异常点（算法标记）</span>';
        }
        return result;
      }
    },
    xAxis: { 
      type: 'category', 
      data: dates,
      axisLabel: { rotate: 45 }
    },
    yAxis: { 
      type: 'value',
      name: '能耗 (kWh)'
    },
    series: [{
      type: 'line',
      data: seriesData,
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      },
      lineStyle: {
        width: 3,
        color: '#409EFF'
      },
      itemStyle: {
        color: '#409EFF'
      }
    }]
  });
  
  // 响应式调整
  window.addEventListener('resize', () => chart.resize());
};

// 更新柱状图
const updateBarChart = () => {
  if (!barChartRef.value) return;
  
  const chart = echarts.getInstanceByDom(barChartRef.value) || echarts.init(barChartRef.value);
  
  // 按建筑分组统计
  const buildingData = {};
  tableData.value.forEach(item => {
    if (!buildingData[item.building]) {
      buildingData[item.building] = 0;
    }
    buildingData[item.building] += item.value;
  });
  
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    xAxis: { 
      type: 'category', 
      data: Object.keys(buildingData),
      axisLabel: { rotate: 0 }
    },
    yAxis: { 
      type: 'value',
      name: '总能耗 (kWh)'
    },
    series: [{
      type: 'bar',
      data: Object.values(buildingData),
      barWidth: '50%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#67c23a' },
          { offset: 1, color: '#95d475' }
        ])
      },
      label: {
        show: true,
        position: 'top',
        formatter: '{c} kWh'
      }
    }]
  });
  
  window.addEventListener('resize', () => chart.resize());
};

// 初始化图表
const initCharts = () => {
  updateLineChart();
  updateBarChart();
};

// 图表放大
const zoomChart = (type) => {
  currentChartType.value = type;
  dialogVisible.value = true;
  
  setTimeout(() => {
    if (zoomChartRef.value) {
      const zoomChart = echarts.init(zoomChartRef.value);
      
      if (type === 'line') {
        // 复制折线图配置
        const option = echarts.getInstanceByDom(lineChartRef.value)?.getOption();
        zoomChart.setOption(option);
      } else {
        // 复制柱状图配置
        const option = echarts.getInstanceByDom(barChartRef.value)?.getOption();
        zoomChart.setOption(option);
      }
      
      window.addEventListener('resize', () => zoomChart.resize());
    }
  }, 100);
};

// 导出报表交互
const exportReport = () => {
  if (tableData.value.length === 0) {
    ElMessage.warning('暂无数据可导出');
    return;
  }
  
  exporting.value = true;
  ElMessage({ message: '报表生成中...', type: 'info', duration: 2000 });
  
  setTimeout(() => {
    exporting.value = false;
    ElMessage.success('报表下载完成');
    // 实际项目中这里应该触发文件下载
    // downloadFile(reportBlob);
  }, 2000);
};

// 模拟 NL2Query API
const mockNL2QueryAPI = async (query) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      // 简单的关键词匹配逻辑
      const buildings = [];
      let parameter = 'electricity';
      const dateRange = [new Date(2024, 2, 1), new Date(2024, 2, 7)];
      
      if (query.includes('A 栋') || query.includes('A')) buildings.push('A');
      if (query.includes('B 栋') || query.includes('B')) buildings.push('B');
      if (query.includes('空调')) parameter = 'ac';
      if (query.includes('温度')) parameter = 'temp';
      if (query.includes('COP')) parameter = 'cop';
      
      resolve({
        buildings: buildings.length > 0 ? buildings : ['A'],
        parameter,
        dateRange
      });
    }, 500);
  });
};

// 生命周期钩子 - 页面加载时初始化
onMounted(() => {
  updateTableData();
  initCharts();
});
</script>

<style scoped>
.dashboard-container { 
  padding: 20px; 
  background: #f5f7fa; 
  min-height: calc(100vh - 84px);
}

.mt-4 { margin-top: 16px; }

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.nl-input-item {
  flex: 1;
  min-width: 300px;
}

.result-tabs {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
}

.chart-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.zoom-icon { 
  cursor: pointer; 
  color: #909399; 
  font-size: 18px;
  transition: color 0.3s;
}

.zoom-icon:hover {
  color: #409EFF;
}

.statistic-card {
  text-align: center;
  padding: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.footer-bar { 
  position: fixed; 
  bottom: 30px; 
  right: 40px; 
  z-index: 100;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: #fff;
  padding: 10px 20px;
}

:deep(.el-statistic__head) {
  font-size: 14px;
  color: #909399;
}

:deep(.el-statistic__content) {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
</style>
