<template>
  <n-card title="能耗排名 TOP5" :bordered="false" content-style="padding: 20px;" class="ranking-card">
    <n-space vertical :size="16">
      <div v-for="(item, index) in rankingList" :key="item.buildingId" class="ranking-item">
        <div class="ranking-info">
          <n-tag :type="getRankingTagType(index)" size="small" class="ranking-tag">
            {{ index + 1 }}
          </n-tag>
          <span class="ranking-building">{{ item.buildingName }}</span>
          <n-progress
            :percentage="item.percentage"
            :color="getRankingColor(index)"
            :show-indicator="false"
            class="ranking-progress"
          />
          <span class="ranking-value">{{ item.energy.toFixed(2) }} MWh</span>
        </div>
      </div>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
interface RankingItem {
  buildingId: string
  buildingName: string
  energy: number
  percentage: number
}

interface Props {
  rankingList: RankingItem[]
}

const props = defineProps<Props>()

// 获取排名标签类型
const getRankingTagType = (index: number) => {
  if (index === 0) return 'error'
  if (index === 1) return 'warning'
  if (index === 2) return 'info'
  return 'default'
}

// 获取排名进度条颜色
const getRankingColor = (index: number) => {
  if (index === 0) return '#f5222d'
  if (index === 1) return '#faad14'
  if (index === 2) return '#1890ff'
  return '#52c41a'
}
</script>

<style scoped lang="scss">
.ranking-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  background: var(--card-bg);
  transition: background 0.3s ease, box-shadow 0.3s ease;
  
  .ranking-item {
    .ranking-info {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .ranking-tag {
        width: 24px;
        text-align: center;
      }
      
      .ranking-building {
        width: 100px;
        font-size: 14px;
        color: var(--text-primary);
      }
      
      .ranking-progress {
        flex: 1;
      }
      
      .ranking-value {
        width: 100px;
        text-align: right;
        font-size: 14px;
        font-weight: 600;
        color: #1890ff;
      }
    }
  }
}
</style>
