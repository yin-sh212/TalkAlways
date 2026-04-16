<template>
  <n-grid :cols="3" :x-gap="12" :y-gap="12" class="kpi-grid">
    <n-grid-item>
      <n-card :bordered="false" class="kpi-card" content-style="padding: 14px;">
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">今日总能耗</span>
            <n-icon size="20" color="#18a058">
              <EnergyIcon />
            </n-icon>
          </n-space>
        </template>
        <n-skeleton v-if="loading" :rows="2" />
        <template v-else>
          <div class="kpi-value">
            {{ kpiData.totalEnergy.toFixed(2) }}
            <span class="unit">MWh</span>
          </div>
          <div class="kpi-changes">
            <div
              class="kpi-change"
              :class="{ 'is-up': kpiData.dayChange >= 0 }"
            >
              <n-icon
                :component="
                  kpiData.dayChange >= 0 ? ArrowUpward : ArrowDownward
                "
                size="14"
              />
              {{ Math.abs(kpiData.dayChange).toFixed(1) }}%
              <span class="change-label">较昨日</span>
            </div>
            <div
              class="kpi-change"
              :class="{ 'is-up': kpiData.weekChange >= 0 }"
            >
              <n-icon
                :component="
                  kpiData.weekChange >= 0 ? ArrowUpward : ArrowDownward
                "
                size="14"
              />
              {{ Math.abs(kpiData.weekChange).toFixed(1) }}%
              <span class="change-label">较上周</span>
            </div>
          </div>
        </template>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card
        :bordered="false"
        class="kpi-card"
        content-style="padding: 14px;"
      >
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">监测点在线率</span>
            <n-icon size="20" color="#1890ff">
              <Device />
            </n-icon>
          </n-space>
        </template>
        <n-skeleton v-if="loading" :rows="2" />
        <template v-else>
          <div class="kpi-value">
            {{ kpiData.deviceOnlineRate }}
            <span class="unit">%</span>
          </div>
          <div class="kpi-subtitle">
            <n-tag
              :type="kpiData.abnormalDeviceCount > 0 ? 'warning' : 'success'"
              size="small"
            >
              异常监测点：{{ kpiData.abnormalDeviceCount }}
            </n-tag>
          </div>
        </template>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card :bordered="false" class="kpi-card" content-style="padding: 14px;">
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">能效比 (COP)</span>
            <n-space align="center">
              <n-tooltip placement="bottom">
                <template #trigger>
                  <n-icon size="18" color="#999" style="cursor: help">
                    <HelpCircleOutline />
                  </n-icon>
                </template>
                <div style="padding: 4px 0">
                  <strong>计算公式：</strong>COP = 制热量 / 输入功率<br />
                  <strong>数据来源：</strong>根据能耗与温差计算得出<br />
                  <strong>指标含义：</strong>数值越高表示能效越好<br />
                  <strong>参考范围：</strong>一般空调系统 COP 在 2.5-4.0 之间
                </div>
              </n-tooltip>
              <n-icon size="20" color="#52c41a">
                <Leaf />
              </n-icon>
            </n-space>
          </n-space>
        </template>
        <n-skeleton v-if="loading" :rows="2" />
        <template v-else>
          <div class="kpi-value">
            {{ kpiData.cop.toFixed(2) }}
          </div>
          <div class="kpi-subtitle">
            <span class="sub-text">根据能耗与温差计算</span>
          </div>
        </template>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import {
  ArrowUpOutline as ArrowUpward,
  ArrowDownOutline as ArrowDownward,
  Flash,
  Leaf,
  TrendingUp,
  FlashOutline as Device,
  Flash as EnergyIcon,
  HelpCircleOutline,
} from "@vicons/ionicons5";
import type { KPIData } from "@/types/dashboard";

interface Props {
  loading: boolean;
  kpiData: KPIData;
}

const props = defineProps<Props>();
</script>

<style scoped lang="scss">
.kpi-grid {
  .kpi-card {
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);

    .card-title {
      font-size: 16px;
      color: #666;
      font-weight: 500;
    }

    .kpi-value {
      font-size: 26px;
      font-weight: bold;
      color: #333;

      .unit {
        font-size: 14px;
        color: #999;
        margin-left: 4px;
      }
    }

    .kpi-changes {
      display: flex;
      gap: 12px;
      margin-top: 6px;

      .kpi-change {
        display: flex;
        align-items: center;
        gap: 3px;
        font-size: 13px;

        &.is-up {
          color: #f5222d;
        }

        &:not(.is-up) {
          color: #52c41a;
        }

        .change-label {
          font-size: 12px;
          color: #999;
          margin-left: 3px;
        }
      }
    }

    .kpi-subtitle {
      margin-top: 6px;

      .sub-text {
        font-size: 13px;
        color: #999;
      }
    }
  }
}
</style>
