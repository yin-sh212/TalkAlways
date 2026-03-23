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
          <n-tag :type="getStatusType(currentDevice.status) as any">
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
import { ref, reactive, computed, h, onMounted } from 'vue'
import { Search, AddCircle, Settings, Warning, CheckmarkCircle, CloseCircle } from '@vicons/ionicons5'
import { NTag, NButton, NIcon, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { getDeviceList, addDevice, deleteDevice, getDeviceStats } from '@/api/device'
import { getBuildings } from '@/api/query'

interface ApiDevice {
  id: string
  name: string
  type: string
  building_id: string
  status: string
  created_at?: string
}

interface Device extends ApiDevice {
  typeName: string
  buildingName: string
  location: string
  commissionDate: string
  lastMaintenance: string
  remark: string
}

interface ApiDeviceStats {
  total_devices: number
  status_stats: Record<string, number>
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
  { label: '运行中', value: 'online' },
  { label: '离线', value: 'offline' },
  { label: '故障', value: 'fault' },
  { label: '维护中', value: 'maintenance' }
]

const buildingOptions = ref<any[]>([])

// 设备数据
const devices = ref<Device[]>([])
const loading = ref(false)

// 设备统计数据
const deviceStatsData = ref<ApiDeviceStats | null>(null)

// 加载建筑列表
const loadBuildings = async () => {
  try {
    const res = await getBuildings()
    if (res.data.code === 200 && res.data.data) {
      buildingOptions.value = res.data.data.map((b: any) => ({
        label: b.name || b.building_name || `建筑${b.id}`,
        value: b.id
      }))
    }
  } catch (error) {
    console.error('加载建筑列表失败:', error)
  }
}

// 加载设备列表
const loadDevices = async () => {
  loading.value = true
  try {
    const res = await getDeviceList(queryForm.deviceType || undefined)
    
    if (res.data.code === 200 && res.data.data) {
      // 将后端返回的数据转换为前端格式
      devices.value = res.data.data.items.map((item: any) => ({
        id: item.id || '',
        name: item.deviceName || '-',
        type: item.deviceType || '',
        building_id: item.building || '',
        status: item.deviceStatus || 'offline',
        typeName: getTypeName(item.deviceType),
        buildingName: getBuildingName(item.building),
        location: '-',
        commissionDate: '-',
        lastMaintenance: '-',
        remark: ''
      }))
    }
  } catch (error) {
    console.error('加载设备列表失败:', error)
    message.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

// 加载设备统计
const loadDeviceStats = async () => {
  try {
    const res = await getDeviceStats()
    if (res.data.code === 200 && res.data.data) {
      deviceStatsData.value = res.data.data
    }
  } catch (error) {
    console.error('加载设备统计失败:', error)
  }
}

// 辅助函数
const getTypeName = (type: string): string => {
  const map: Record<string, string> = {
    hvac: '空调机组',
    pump: '水泵',
    fan: '风机',
    sensor: '传感器',
    meter: '电表',
    other: '其他'
  }
  return map[type] || type
}

const getBuildingName = (buildingId: string): string => {
  const building = buildingOptions.value.find(b => b.value === buildingId)
  return building?.label || buildingId
}

// 设备统计卡片
const deviceStats = computed(() => {
  if (!deviceStatsData.value) {
    return [
      { title: '设备总数', value: devices.value.length, icon: Settings, color: '#1890ff' },
      { title: '运行中', value: devices.value.filter(d => d.status === 'online').length, icon: CheckmarkCircle, color: '#52c41a' },
      { title: '故障', value: devices.value.filter(d => d.status === 'fault').length, icon: CloseCircle, color: '#f5222d' },
      { title: '维护中', value: devices.value.filter(d => d.status === 'maintenance').length, icon: Warning, color: '#fa8c16' }
    ]
  }
  
  return [
    { 
      title: '设备总数', 
      value: deviceStatsData.value.total_devices, 
      icon: Settings, 
      color: '#1890ff' 
    },
    { 
      title: '运行中', 
      value: deviceStatsData.value.status_stats['online'] || 0, 
      icon: CheckmarkCircle, 
      color: '#52c41a' 
    },
    { 
      title: '故障', 
      value: deviceStatsData.value.status_stats['fault'] || 0, 
      icon: CloseCircle, 
      color: '#f5222d' 
    },
    { 
      title: '维护中', 
      value: deviceStatsData.value.status_stats['maintenance'] || 0, 
      icon: Warning, 
      color: '#fa8c16' 
    }
  ]
})

// 过滤后的设备列表
const filteredDevices = computed(() => {
  return devices.value.filter(device => {
    if (queryForm.deviceType && device.type !== queryForm.deviceType) return false
    if (queryForm.status && device.status !== queryForm.status) return false
    if (queryForm.building && device.building_id !== queryForm.building) return false
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
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: any) => {
      return h(NTag, {
        type: getStatusType(row.status as string) as any,
        size: 'small',
        bordered: false
      }, { default: () => getStatusText(row.status as string) })
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right',
    render: (row: any) => {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
        h(NButton, {
          size: 'small',
          onClick: () => showDeviceDetail(row as Device)
        }, { default: () => '详情' }),
        h(NButton, {
          size: 'small',
          type: 'warning',
          onClick: () => handleEditDevice(row as Device)
        }, { default: () => '编辑' }),
        h(NButton, {
          size: 'small',
          type: 'error',
          onClick: () => handleDeleteDevice(row as Device)
        }, { default: () => '删除' })
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
    online: 'success',
    offline: 'default',
    fault: 'error',
    maintenance: 'warning'
  }
  return map[status] || 'default'
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    online: '运行中',
    offline: '离线',
    fault: '故障',
    maintenance: '维护中'
  }
  return map[status] || '未知'
}

const handleQuery = () => {
  loadDevices()
}

const handleReset = () => {
  queryForm.deviceType = ''
  queryForm.status = ''
  queryForm.building = ''
  loadDevices()
}

const handleAddDevice = async () => {
  try {
    await addFormRef.value?.validate()
    adding.value = true
    
    const res = await addDevice({
      name: addForm.name,
      type: addForm.type,
      building_id: addForm.building,
      status: addForm.status
    })
    
    if (res.data.code === 200) {
      message.success('添加成功')
      showAddModal.value = false
      loadDevices()
      loadDeviceStats()
      
      // 重置表单
      Object.assign(addForm, {
        name: '',
        type: '',
        building: '',
        location: '',
        commissionDate: null,
        status: 'online',
        remark: ''
      })
    } else {
      message.error(res.data.message || '添加失败')
    }
  } catch (error: any) {
    console.error('添加设备失败:', error)
    message.error(error.response?.data?.message || '添加失败')
  } finally {
    adding.value = false
  }
}

const handleEditDevice = async (row: Device) => {
  message.info('编辑功能开发中')
  // TODO: 实现编辑功能
}

const handleDeleteDevice = async (row: Device) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除设备"${row.name}"吗？此操作为软删除，可在数据库中恢复。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await deleteDevice(row.id)
        if (res.data.code === 200) {
          message.success('删除成功')
          loadDevices()
          loadDeviceStats()
        } else {
          message.error(res.data.message || '删除失败')
        }
      } catch (error: any) {
        console.error('删除设备失败:', error)
        message.error(error.response?.data?.message || '删除失败')
      }
    }
  })
}

const showDeviceDetail = (device: Device) => {
  currentDevice.value = device
  showDetailModal.value = true
}

// 生命周期
onMounted(() => {
  loadBuildings()
  loadDevices()
  loadDeviceStats()
})
</script>