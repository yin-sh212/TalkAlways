<template>
  <n-grid :cols="3" :x-gap="16" :y-gap="16" class="kpi-grid">
    <n-grid-item>
      <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">今日总能耗</span>
            <n-icon size="24" color="#18a058">
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
            <div class="kpi-change" :class="{ 'is-up': kpiData.dayChange >= 0 }">
              <n-icon :component="kpiData.dayChange >= 0 ? ArrowUpward : ArrowDownward" />
              {{ Math.abs(kpiData.dayChange).toFixed(1) }}%
              <span class="change-label">较昨日</span>
            </div>
            <div class="kpi-change" :class="{ 'is-up': kpiData.weekChange >= 0 }">
              <n-icon :component="kpiData.weekChange >= 0 ? ArrowUpward : ArrowDownward" />
              {{ Math.abs(kpiData.weekChange).toFixed(1) }}%
              <span class="change-label">较上周</span>
            </div>
          </div>
        </template>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">在线设备率</span>
            <n-icon size="24" color="#1890ff">
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
            <n-tag :type="kpiData.abnormalDeviceCount > 0 ? 'warning' : 'success'" size="small">
              异常设备：{{ kpiData.abnormalDeviceCount }}
            </n-tag>
          </div>
        </template>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">能效比 (COP)</span>
            <n-icon size="24" color="#52c41a">
              <Leaf />
            </n-icon>
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
    
    <!-- <n-grid-item>
      <n-card :bordered="false" class="kpi-card" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between" align="center">
            <span class="card-title">今日 CO₂减排</span>
            <n-icon size="24" color="#52c41a">
              <Leaf />
            </n-icon>
          </n-space>
        </template>
        <n-skeleton v-if="loading" :rows="2" />
        <template v-else>
          <div class="kpi-value">
            {{ kpiData.co2Reduction.toFixed(1) }}
            <span class="unit">kg</span>
          </div>
          <div class="kpi-subtitle">
            <span class="sub-text">根据能耗换算</span>
          </div>
        </template>
      </n-card>
    </n-grid-item> -->
  </n-grid>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Flash, Leaf, TrendingUp, FlashOutline as Device, Flash as EnergyIcon } from '@vicons/ionicons5'
import { 
  ArrowUpOutline as ArrowUpward, 
  ArrowDownOutline as ArrowDownward 
} from '@vicons/ionicons5'
import type { KPIData } from '@/types/dashboard'

interface Props {
  loading: boolean
  kpiData: KPIData
}

const props = defineProps<Props>()
</script>

<style scoped lang="scss">
.kpi-grid {
  .kpi-card {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    
    .card-title {
      font-size: 14px;
      color: #666;
      font-weight: 500;
    }

    .kpi-value {
      font-size: 32px;
      font-weight: bold;
      color: #333;
      margin: 16px 0;

      .unit {
        font-size: 14px;
        color: #999;
        margin-left: 4px;
      }
    }

    .kpi-changes {
      display: flex;
      gap: 16px;
      margin-top: 8px;

      .kpi-change {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 14px;
        
        &.is-up {
          color: #f5222d;
        }
        
        &:not(.is-up) {
          color: #52c41a;
        }

        .change-label {
          font-size: 12px;
          color: #999;
          margin-left: 4px;
        }
      }
    }

    .kpi-subtitle {
      margin-top: 8px;

      .sub-text {
        font-size: 12px;
        color: #999;
      }
    }
  }
}
</style>