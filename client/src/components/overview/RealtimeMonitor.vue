<template>
  <div class="realtime-monitor">
    <div class="header">
      <h2>📡 历史数据回放</h2>
      <div class="controls">
        <button @click="startPlayback" :disabled="isPlaying" class="btn-start">
          ▶️ 开始回放
        </button>
        <button @click="stopPlayback" :disabled="!isPlaying" class="btn-stop">
          ⏹️ 停止回放
        </button>
        <button @click="clearData" class="btn-clear">
          🗑️ 清空列表
        </button>
      </div>
    </div>

    <!-- 状态面板 -->
    <div class="status-panel">
      <div class="status-item">
        <span class="label">状态:</span>
        <span :class="['value', isPlaying ? 'playing' : 'stopped']">
          {{ isPlaying ? '🟢 回放中' : '🔴 已停止' }}
        </span>
      </div>
      <div class="status-item">
        <span class="label">当前时间:</span>
        <span class="value">{{ currentTime || '-' }}</span>
      </div>
      <div class="status-item">
        <span class="label">进度:</span>
        <span class="value">{{ progressPercent }}%</span>
      </div>
      <div class="status-item">
        <span class="label">接收数据:</span>
        <span class="value">{{ receivedCount }} 条</span>
      </div>
    </div>

    <!-- 配置表单 -->
    <div class="config-form">
      <div class="form-row">
        <label>回放起始:</label>
        <input v-model="config.startDate" type="datetime-local" />
      </div>
      <div class="form-row">
        <label>回放结束:</label>
        <input v-model="config.endDate" type="datetime-local" />
      </div>
      <div class="form-row">
        <label>播放速度:</label>
        <select v-model.number="config.speed">
          <option :value="1">1x (实时)</option>
          <option :value="10">10x (快进)</option>
          <option :value="60">60x (快速)</option>
          <option :value="100">100x (超快)</option>
          <option :value="360">360x (极速)</option>
        </select>
      </div>
      <div class="form-row">
        <label>每批数据:</label>
        <select v-model.number="config.batchHours">
          <option :value="1">1 小时</option>
          <option :value="2">2 小时</option>
          <option :value="6">6 小时</option>
          <option :value="12">12 小时</option>
          <option :value="24">24 小时</option>
        </select>
      </div>
      <div class="form-row">
        <label>建筑过滤:</label>
        <input v-model="config.buildingId" placeholder="留空表示所有建筑" />
      </div>
    </div>

    <!-- 提示信息 -->
    <div class="info-box">
      <strong>💡 使用说明：</strong>
      <ul>
        <li>从数据集中按时间顺序读取历史数据，模拟准实时采集过程</li>
        <li><strong>1x 速度</strong>: 现实 1 秒 = 模拟 1 秒（真实时间回放）</li>
        <li><strong>10x 速度</strong>: 现实 1 秒 = 模拟 10 秒（10 倍速快进）</li>
        <li><strong>100x 速度</strong>: 现实 1 分钟 = 模拟 100 分钟（超快进模式）</li>
        <li>示例：回放 9 月份整月数据（30 天），使用 100x 速度仅需约 7 分钟</li>
      </ul>
    </div>

    <!-- 实时数据列表 -->
    <div class="data-list">
      <h3>最新数据 (最近 {{ recentRecords.length }} 条)</h3>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>时间戳</th>
              <th>建筑 ID</th>
              <th>设备 ID</th>
              <th>用电量 (kWh)</th>
              <th>温度 (℃)</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(record, index) in recentRecords" :key="index" :class="{ anomaly: record.is_anomaly }">
              <td>{{ formatTimestamp(record.timestamp) }}</td>
              <td>{{ record.building_id }}</td>
              <td>{{ record.meter_id }}</td>
              <td>{{ record.electricity?.toFixed(2) }}</td>
              <td>{{ record.ambient_temp?.toFixed(1) }}</td>
              <td>
                <span :class="['badge', record.is_anomaly ? 'badge-anomaly' : 'badge-normal']">
                  {{ record.is_anomaly ? '异常' : '正常' }}
                </span>
              </td>
            </tr>
            <tr v-if="recentRecords.length === 0">
              <td colspan="6" class="empty">暂无数据，点击"开始回放"</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const isPlaying = ref(false)
const currentTime = ref(null)
const progressPercent = ref(0)
const receivedCount = ref(0)
const recentRecords = ref([])

const config = reactive({
  startDate: '2016-09-01T00:00:00',
  endDate: '2016-09-30T23:59:59',
  speed: 100,
  batchHours: 1,
  buildingId: ''
})

let eventSource = null

// 开始回放
const startPlayback = async () => {
  try {
    // 先关闭之前的连接
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    
    const params = new URLSearchParams({
      start_date: config.startDate.replace('T', ' '),
      end_date: config.endDate.replace('T', ' '),
      speed: config.speed.toString(),
      batch_hours: config.batchHours.toString(),
      building_id: config.buildingId
    })
    
    // 连接到 SSE 流
    eventSource = new EventSource(
      `http://localhost:3000/api/realtime/stream?${params}`
    )
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'start') {
          ElMessage.success(data.message)
          isPlaying.value = true
        } 
        else if (data.type === 'data') {
          // 添加新数据到列表头部
          if (data.records && data.records.length > 0) {
            recentRecords.value = [...data.records, ...recentRecords.value].slice(0, 100)
            receivedCount.value += data.records.length
            
            // 更新当前时间
            if (data.batch_end) {
              currentTime.value = formatTimestamp(data.batch_end)
            }
          }
        } 
        else if (data.type === 'progress') {
          progressPercent.value = data.progress_percent
        }
        else if (data.type === 'complete') {
          ElMessage.success(`回放完成！共 ${data.total_batches} 批次`)
          stopPlayback()
        }
        else if (data.type === 'error') {
          ElMessage.error(`流错误：${data.message}`)
          stopPlayback()
        }
      } catch (error) {
        console.error('解析 SSE 数据失败:', error)
      }
    }
    
    eventSource.onerror = () => {
      console.error('SSE 连接错误')
      ElMessage.error('连接中断')
      stopPlayback()
    }
    
  } catch (error) {
    ElMessage.error(`启动失败：${error.message}`)
  }
}

// 停止回放
const stopPlayback = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  isPlaying.value = false
}

// 清空数据
const clearData = () => {
  recentRecords.value = []
  receivedCount.value = 0
  progressPercent.value = 0
  currentTime.value = null
  ElMessage.success('数据已清空')
}

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})
</script>

<style scoped lang="scss">
.realtime-monitor {
  padding: 20px;
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
      font-size: 24px;
    }
    
    .controls {
      button {
        margin-left: 10px;
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        
        &:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        &.btn-start {
          background-color: #52c41a;
          color: white;
          
          &:hover:not(:disabled) {
            background-color: #73d13d;
          }
        }
        
        &.btn-stop {
          background-color: #ff4d4f;
          color: white;
          
          &:hover:not(:disabled) {
            background-color: #ff7875;
          }
        }
        
        &.btn-clear {
          background-color: #1890ff;
          color: white;
          
          &:hover {
            background-color: #40a9ff;
          }
        }
      }
    }
  }
  
  .status-panel {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background: #f5f5f5;
    border-radius: 8px;
    
    .status-item {
      display: flex;
      flex-direction: column;
      
      .label {
        font-size: 12px;
        color: #666;
        margin-bottom: 5px;
      }
      
      .value {
        font-size: 18px;
        font-weight: bold;
        
        &.playing {
          color: #52c41a;
        }
        
        &.stopped {
          color: #ff4d4f;
        }
      }
    }
  }
  
  .config-form {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background: #fafafa;
    border-radius: 8px;
    
    .form-row {
      display: flex;
      align-items: center;
      
      label {
        width: 100px;
        font-size: 14px;
        color: #333;
      }
      
      input, select {
        flex: 1;
        padding: 8px;
        border: 1px solid #d9d9d9;
        border-radius: 4px;
        font-size: 14px;
      }
    }
  }
  
  .info-box {
    margin-bottom: 20px;
    padding: 15px;
    background: #e6f7ff;
    border-left: 4px solid #1890ff;
    border-radius: 4px;
    
    strong {
      color: #0050b3;
      display: block;
      margin-bottom: 8px;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        margin: 4px 0;
        color: #333;
        font-size: 14px;
      }
    }
  }
  
  .data-list {
    h3 {
      margin: 0 0 10px 0;
      font-size: 18px;
    }
    
    .table-container {
      overflow-x: auto;
      
      table {
        width: 100%;
        border-collapse: collapse;
        
        th, td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid #e8e8e8;
        }
        
        th {
          background: #fafafa;
          font-weight: 600;
        }
        
        tbody {
          tr {
            &:hover {
              background: #f5f5f5;
            }
            
            &.anomaly {
              background: #fff1f0;
              
              td:last-child {
                .badge {
                  background: #ff4d4f;
                  color: white;
                }
              }
            }
            
            .empty {
              text-align: center;
              color: #999;
              padding: 40px;
            }
            
            .badge {
              padding: 4px 8px;
              border-radius: 4px;
              font-size: 12px;
              
              &.badge-normal {
                background: #f6ffed;
                color: #52c41a;
              }
              
              &.badge-anomaly {
                background: #fff1f0;
                color: #ff4d4f;
              }
            }
          }
        }
      }
    }
  }
}
</style>
