<template>
  <n-grid :cols="24" :x-gap="16" :y-gap="16">
    <!-- 总告警数 -->
    <n-grid-item :span="6">
      <n-card :bordered="false" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between">
            <span class="metric-title">总告警数</span>
            <n-icon size="24" color="#f5222d">
              <Alert />
            </n-icon>
          </n-space>
        </template>
        <div class="metric-value" style="color: #f5222d;">
          {{ metrics.totalAlarms }}
        </div>
        <div class="metric-footer">
          <n-text depth="3">当前时段告警总数</n-text>
        </div>
      </n-card>
    </n-grid-item>

    <!-- 未解决告警 -->
    <n-grid-item :span="6">
      <n-card :bordered="false" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between">
            <span class="metric-title">未解决告警</span>
            <n-icon size="24" color="#fa8c16">
              <Warning />
            </n-icon>
          </n-space>
        </template>
        <div class="metric-value" style="color: #fa8c16;">
          {{ metrics.unresolvedCount }}
        </div>
        <div class="metric-footer">
          <n-text depth="3">需要处理的告警</n-text>
        </div>
      </n-card>
    </n-grid-item>

    <!-- 紧急告警 -->
    <n-grid-item :span="6">
      <n-card :bordered="false" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between">
            <span class="metric-title">紧急告警</span>
            <n-icon size="24" color="#ff4d4f">
              <Flash />
            </n-icon>
          </n-space>
        </template>
        <div class="metric-value" style="color: #ff4d4f;">
          {{ metrics.criticalCount }}
        </div>
        <div class="metric-footer">
          <n-text depth="3">需立即处理</n-text>
        </div>
      </n-card>
    </n-grid-item>

    <!-- 已确认告警 -->
    <n-grid-item :span="6">
      <n-card :bordered="false" content-style="padding: 20px;">
        <template #header>
          <n-space justify="space-between">
            <span class="metric-title">已确认告警</span>
            <n-icon size="24" color="#52c41a">
              <CheckmarkCircle />
            </n-icon>
          </n-space>
        </template>
        <div class="metric-value" style="color: #52c41a;">
          {{ metrics.acknowledgedCount }}
        </div>
        <div class="metric-footer">
          <n-text depth="3">已确认的告警</n-text>
        </div>
      </n-card>
    </n-grid-item>
  </n-grid>
</template>

<script setup lang="ts">
import { Alert, Warning, Flash, CheckmarkCircle } from '@vicons/ionicons5'

interface AlarmMetrics {
  totalAlarms: number
  unresolvedCount: number
  criticalCount: number
  acknowledgedCount: number
}

defineProps<{
  metrics: AlarmMetrics
  loading?: boolean
}>()
</script>

<style scoped>
.metric-title {
  font-size: 17px;
  color: #666;
}

.metric-value {
  font-size: 30px;
  font-weight: bold;
}

.metric-footer {
  margin-top: 8px;
  font-size: 14px;
}
</style>
