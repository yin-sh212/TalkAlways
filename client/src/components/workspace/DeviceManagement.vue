<template>
  <div class="device-management">
    <!-- 查询条件 -->
    <n-card :bordered="false" content-style="padding: 16px;" style="margin-bottom: 16px;">
      <n-form :model="queryForm" inline label-placement="left">
        <n-space :size="16">
          <n-form-item label="设备类型">
            <n-select
              v-model:value="queryForm.deviceType"
             placeholder="全部类型"
              :options="deviceTypeOptions"
              clearable
              style="width: 180px"
            />
          </n-form-item>
          
          <n-form-item label="状态">
            <n-select
              v-model:value="queryForm.status"
             placeholder="全部状态"
              :options="statusOptions"
              clearable
              style="width: 150px"
            />
          </n-form-item>
          
          <n-form-item label="所属建筑">
            <n-select
              v-model:value="queryForm.building"
             placeholder="全部建筑"
              :options="buildingOptions"
              clearable
              style="width: 180px"
            />
          </n-form-item>
          
          <n-form-item>
            <n-space>
              <n-button type="primary" @click="handleQuery">
                <template #icon>
                  <n-icon :component="Search" />
                </template>
                查询
              </n-button>
              <n-button @click="handleReset">重置</n-button>
              <n-button type="success" @click="showAddModal = true">
                <template #icon>
                  <n-icon :component="AddCircle" />
                </template>
                新增设备
              </n-button>
            </n-space>
          </n-form-item>
        </n-space>
      </n-form>
    </n-card>

    <!-- 设备统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" style="margin-bottom: 20px;">
      <n-grid-item v-for="stat in deviceStats" :key="stat.title">
        <n-card :bordered="false" embedded>
          <template #header>
            <n-space align="center">
              <n-icon :component="stat.icon" :color="stat.color" size="24" />
              <span style="font-size: 14px; color: var(--text-secondary)">{{ stat.title }}</span>
            </n-space>
          </template>
          <div style="font-size: 28px; font-weight: bold; color: var(--text-primary)">
            {{ stat.value }}
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 设备列表 -->
    <n-card title="设备列表" :bordered="false">
      <n-data-table
        :columns="columns"
        :data="filteredDevices"
        :loading="loading"
        :pagination="pagination"
        :row-key="(row) => row.id"
        striped
      />
    </n-card>

    <!-- 新增设备弹窗 -->
    <n-modal
      v-model:show="showAddModal"
     preset="card"
     title="新增设备"
      style="width: 600px"
    >
      <n-form
       ref="addFormRef"
        :model="addForm"
        :rules="addRules"
       label-placement="left"
       label-width="100px"
      >
        <n-form-item label="设备名称" path="name">
          <n-input v-model:value="addForm.name" placeholder="请输入设备名称" />
        </n-form-item>
        
        <n-form-item label="设备类型" path="type">
          <n-select
           v-model:value="addForm.type"
            :options="deviceTypeOptions"
           placeholder="请选择设备类型"
          />
        </n-form-item>
        
        <n-form-item label="所属建筑" path="building">
          <n-select
            v-model:value="addForm.building"
            :options="buildingOptions"
           placeholder="请选择建筑"
          />
        </n-form-item>
        
        <n-form-item label="安装位置" path="location">
          <n-input v-model:value="addForm.location" placeholder="例如：B1 层空调机房" />
        </n-form-item>
        
        <n-form-item label="投运日期" path="commissionDate">
          <n-date-picker
            v-model:value="addForm.commissionDate"
            type="date"
           placeholder="选择日期"
            style="width: 100%"
          />
        </n-form-item>
        
        <n-form-item label="状态" path="status">
          <n-select
            v-model:value="addForm.status"
            :options="statusOptions"
           placeholder="请选择状态"
          />
        </n-form-item>
        
        <n-form-item label="备注">
          <n-input
            v-model:value="addForm.remark"
            type="textarea"
           placeholder="设备备注信息"
            :rows="3"
          />
        </n-form-item>
      </n-form>
      
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="handleAddDevice" :loading="adding">
            确定
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 设备详情弹窗 -->
    <n-modal
      v-model:show="showDetailModal"
     preset="card"
     title="设备详情"
      style="width: 800px"
    >
      <n-descriptions bordered :column="2" v-if="currentDevice">
        <n-descriptions-item label="设备 ID">{{ currentDevice.id }}</n-descriptions-item>
        <n-descriptions-item label="设备名称">{{ currentDevice.name }}</n-descriptions-item>
        <n-descriptions-item label="设备类型">{{ currentDevice.typeName }}</n-descriptions-item>
        <n-descriptions-item label="所属建筑">{{ currentDevice.buildingName }}</n-descriptions-item>
        <n-descriptions-item label="安装位置">{{ currentDevice.location }}</n-descriptions-item>
        <n-descriptions-item label="投运日期">{{ currentDevice.commissionDate }}</n-descriptions-item>
        <n-descriptions-item label="运行状态">
          <n-tag :type="getStatusType(currentDevice.status)">
            {{ getStatusText(currentDevice.status) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="最后维护日期">{{ currentDevice.lastMaintenance }}</n-descriptions-item>
        <n-descriptions-item label="备注" :span="2">{{ currentDevice.remark }}</n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h } from 'vue'
import { Search, AddCircle, Settings, Warning, CheckmarkCircle, CloseCircle } from '@vicons/ionicons5'
import { NTag, NButton, NIcon, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'

interface Device {
  id: string
  name: string
  type: string
  typeName: string
  building: string
  buildingName: string
  location: string
  commissionDate: string
  status: string
  lastMaintenance: string
  remark: string
}

const message = useMessage()
const dialog = useDialog()

// 查询表单
const queryForm = reactive({
  deviceType: '',
  status: '',
  building: ''
})

// 选项数据
const deviceTypeOptions = [
  { label: '空调机组', value: 'hvac' },
  { label: '水泵', value: 'pump' },
  { label: '风机', value: 'fan' },
  { label: '传感器', value: 'sensor' },
  { label: '电表', value: 'meter' },
  { label: '其他', value: 'other' }
]

const statusOptions = [
  { label: '运行中', value: 'running', style: { color: '#52c41a' } },
  { label: '待机', value: 'standby', style: { color: '#1890ff' } },
  { label: '故障', value: 'fault', style: { color: '#f5222d' } },
  { label: '维修中', value: 'maintenance', style: { color: '#fa8c16' } },
  { label: '停用', value: 'offline', style: { color: '#999' } }
]

const buildingOptions = [
  { label: '行政楼', value: 'building-001' },
  { label: '教学楼 A', value: 'building-002' },
  { label: '教学楼 B', value: 'building-003' },
  { label: '图书馆', value: 'building-004' },
  { label: '实验楼', value: 'building-005' }
]

// Mock 设备数据
const devices = ref<Device[]>([
  {
    id: 'DEV001',
   name: '1#空调机组',
   type: 'hvac',
    typeName: '空调机组',
    building: 'building-001',
    buildingName: '行政楼',
    location: '屋顶机房',
   commissionDate: '2023-01-15',
    status: 'running',
   lastMaintenance: '2024-02-20',
   remark: '定期更换滤网'
  },
  {
    id: 'DEV002',
   name: '2#循环水泵',
   type: 'pump',
    typeName: '水泵',
    building: 'building-002',
    buildingName: '教学楼 A',
    location: '地下泵房',
   commissionDate: '2023-03-10',
    status: 'running',
   lastMaintenance: '2024-01-15',
   remark: '注意检查密封性'
  },
  {
    id: 'DEV003',
   name: '温湿度传感器 -301',
   type: 'sensor',
    typeName: '传感器',
    building: 'building-003',
    buildingName: '教学楼 B',
    location: '301 教室',
   commissionDate: '2023-06-01',
    status: 'fault',
   lastMaintenance: '2024-02-28',
   remark: '需要校准'
  }
])

// 设备统计
const deviceStats = computed(() => [
  {
   title: '设备总数',
    value: devices.value.length,
    icon: Settings,
   color: '#1890ff'
  },
  {
   title: '运行中',
    value: devices.value.filter(d => d.status === 'running').length,
    icon: CheckmarkCircle,
   color: '#52c41a'
  },
  {
   title: '故障',
    value: devices.value.filter(d => d.status === 'fault').length,
    icon: CloseCircle,
   color: '#f5222d'
  },
  {
   title: '维修中',
    value: devices.value.filter(d => d.status === 'maintenance').length,
    icon: Warning,
   color: '#fa8c16'
  }
])

// 过滤后的设备列表
const filteredDevices = computed(() => {
  return devices.value.filter(device => {
    if (queryForm.deviceType && device.type !== queryForm.deviceType) return false
    if (queryForm.status && device.status !== queryForm.status) return false
    if (queryForm.building && device.building !== queryForm.building) return false
   return true
  })
})

// 表格列定义
const columns: DataTableColumns = [
  {
   title: '设备 ID',
   key: 'id',
    width: 100,
    fixed: 'left'
  },
  {
   title: '设备名称',
   key: 'name',
    width: 150,
    ellipsis: { tooltip: true }
  },
  {
   title: '设备类型',
   key: 'typeName',
    width: 120
  },
  {
   title: '所属建筑',
   key: 'buildingName',
    width: 120
  },
  {
   title: '安装位置',
   key: 'location',
    width: 150,
    ellipsis: { tooltip: true }
  },
  {
   title: '状态',
   key: 'status',
    width: 100,
   render: (row: Device) => {
     return h(NTag, {
        type: getStatusType(row.status) as any,
        size: 'small',
        bordered: false
      }, { default: () => getStatusText(row.status) })
    }
  },
  {
   title: '投运日期',
   key: 'commissionDate',
    width: 120
  },
  {
   title: '操作',
   key: 'actions',
    width: 180,
    fixed: 'right',
   render: (row: Device) => {
     return h('div', { style: { display: 'flex', gap: '8px' } }, [
        h(NButton, {
          size: 'small',
          onClick: () => showDeviceDetail(row)
        }, { default: () => '详情' }),
        h(NButton, {
          size: 'small',
         type: 'warning',
          onClick: () => message.info('编辑功能开发中')
        }, { default: () => '编辑' })
      ])
    }
  }
]

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 10,
  pageSizes: [10, 20, 50],
  showSizePicker: true,
  onChange: (page: number) => {
   pagination.page = page
  },
  onUpdatePageSize: (pageSize: number) => {
   pagination.pageSize = pageSize
   pagination.page = 1
  }
})

// 新增设备
const showAddModal = ref(false)
const adding = ref(false)
const addFormRef = ref<any>(null)
const addForm = reactive({
  name: '',
  type: '',
  building: '',
  location: '',
  commissionDate: null,
  status: 'standby',
  remark: ''
})

const addRules = {
  name: { required: true, message: '请输入设备名称', trigger: 'blur' },
  type: { required: true, message: '请选择设备类型', trigger: 'change' },
  building: { required: true, message: '请选择建筑', trigger: 'change' },
  location: { required: true, message: '请输入安装位置', trigger: 'blur' },
  commissionDate: { required: true, message: '请选择投运日期', trigger: 'change' }
}

// 设备详情
const showDetailModal = ref(false)
const currentDevice = ref<Device | null>(null)

// 辅助函数
function getStatusType(status: string): string {
  const map: Record<string, string> = {
    running: 'success',
    standby: 'info',
    fault: 'error',
    maintenance: 'warning',
    offline: 'default'
  }
  return map[status] || 'default'
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    running: '运行中',
    standby: '待机',
    fault: '故障',
    maintenance: '维修中',
    offline: '停用'
  }
  return map[status] || '未知'
}

// 事件处理
const loading = ref(false)

const handleQuery = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
   message.success('查询成功')
  }, 500)
}

const handleReset = () => {
  queryForm.deviceType = ''
  queryForm.status = ''
  queryForm.building = ''
}

const handleAddDevice = async () => {
  try {
   await addFormRef.value?.validate()
    adding.value = true
    
    // TODO: 调用后端接口
   setTimeout(() => {
     const newDevice: Device = {
        id: `DEV${String(devices.value.length + 1).padStart(3, '0')}`,
       name: addForm.name,
       type: addForm.type,
        typeName: deviceTypeOptions.find(o => o.value === addForm.type)?.label || '',
        building: addForm.building,
        buildingName: buildingOptions.find(o => o.value === addForm.building)?.label || '',
        location: addForm.location,
       commissionDate: String(addForm.commissionDate),
        status: addForm.status,
       lastMaintenance: '-',
       remark: addForm.remark
      }
      
      devices.value.push(newDevice)
     message.success('添加成功')
      showAddModal.value = false
      adding.value = false
      
      // 重置表单
      Object.assign(addForm, {
       name: '',
       type: '',
        building: '',
        location: '',
       commissionDate: null,
        status: 'standby',
       remark: ''
      })
    }, 1000)
  } catch (e) {
   console.error(e)
  }
}

const showDeviceDetail = (device: Device) => {
  currentDevice.value = device
  showDetailModal.value = true
}
</script>

<style scoped>
.device-management {
  min-height: 100%;
}
</style>
