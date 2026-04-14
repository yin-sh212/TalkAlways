<template>
  <div class="space-editor">
    <n-card title="空间编辑器" size="small">
      <!-- 工具栏 -->
      <n-space style="margin-bottom: 16px">
        <n-upload
          accept=".dxf"
          :show-file-list="false"
          @before-upload="handleCadUpload"
        >
          <n-button type="info">
            导入CAD底图
          </n-button>
        </n-upload>
        
        <n-divider vertical />
        
        <n-button 
          type="primary" 
          :disabled="!floor"
          @click="startDrawing"
        >
          开始绘制
        </n-button>
        <n-button 
          type="success"
          :disabled="!isDrawing || drawingPoints.length < 3"
          @click="finishDrawing"
        >
          完成绘制 ({{ drawingPoints.length }}/3)
        </n-button>
        <n-button 
          @click="cancelDrawing"
          :disabled="!isDrawing"
        >
          取消绘制
        </n-button>
        <n-button 
          type="success"
          :disabled="!canSave"
          @click="saveSpace"
        >
          保存空间
        </n-button>
        <n-button 
          type="error"
          :disabled="!selectedSpace"
          @click="deleteSpace"
        >
          删除空间
        </n-button>
      </n-space>

      <!-- 绘图提示 -->
      <n-alert v-if="isDrawing" type="info" style="margin-bottom: 16px">
        点击平面图添加顶点，双击或点击"完成"闭合多边形
      </n-alert>

      <!-- 表单区域 -->
      <n-form
        v-if="showForm"
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="left"
        label-width="80"
      >
        <n-form-item label="空间名称" path="name">
          <n-input v-model:value="formData.name" placeholder="例如：会议室A" />
        </n-form-item>
        <n-form-item label="空间编号" path="code">
          <n-input v-model:value="formData.code" placeholder="例如：1A" />
        </n-form-item>
        <n-form-item label="空间类型">
          <n-radio-group v-model:value="formData.space_type">
            <n-radio value="room">房间</n-radio>
            <n-radio value="area">区域</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="面积">
          <n-input-number 
            v-model:value="formData.area_sqm" 
            :min="0"
            :precision="2"
            disabled
          />
          <span style="margin-left: 8px">㎡（自动计算）</span>
        </n-form-item>
      </n-form>

      <!-- 顶点列表 -->
      <n-divider v-if="drawingPoints.length > 0" title-placement="left">
        顶点坐标
      </n-divider>
      <n-data-table
        v-if="drawingPoints.length > 0"
        :columns="pointColumns"
        :data="drawingPoints"
        :pagination="false"
        size="small"
        style="margin-bottom: 16px"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useMessage } from 'naive-ui'
import type { Floor, Space } from '@/types/building'

interface Props {
  floor: Floor | null
  spaces: Space[]
  selectedSpace?: Space | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'space-created', space: Space): void
  (e: 'space-deleted', spaceId: string): void
  (e: 'drawing-mode-change', isDrawing: boolean): void
}>()

const message = useMessage()

// 监听 selectedSpace 变化，自动选中
watch(() => props.selectedSpace, (newSpace) => {
  if (newSpace && props.floor?.id === newSpace.floor_id) {
    selectSpace(newSpace)
  }
}, { immediate: true })

// 状态管理
const isDrawing = ref(false)
const drawingPoints = ref<[number, number][]>([])
const showForm = ref(false)
const selectedSpace = ref<Space | null>(null)

// 表单数据
const formData = ref({
  name: '',
  code: '',
  space_type: 'room' as 'room' | 'area',
  area_sqm: 0
})

// 表单验证规则
const formRules = {
  name: { required: true, message: '请输入空间名称', trigger: 'blur' },
  code: { required: true, message: '请输入空间编号', trigger: 'blur' }
}

// 是否可以保存
const canSave = computed(() => {
  return drawingPoints.value.length >= 3 && formData.value.name && formData.value.code
})

// 顶点表格列定义
const pointColumns = [
  { title: '序号', key: 'index', width: 60 },
  { title: 'X', key: 'x', width: 80 },
  { title: 'Y', key: 'y', width: 80 }
]

// CAD上传处理
const handleCadUpload = async ({ file }: { file: any }) => {
  if (!props.floor) {
    message.warning('请先选择楼层')
    return false
  }
  
  const formData = new FormData()
  formData.append('file', file.file)
  formData.append('floor_id', props.floor.id) // 传递楼层ID
  
  try {
    const response = await fetch('/api/floor/upload-cad', {
      method: 'POST',
      body: formData
    })
    
    const result = await response.json()
    
    if (result.code === 200) {
      message.success('CAD底图导入成功,页面将自动刷新')
      // 延迟刷新以显示提示
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } else {
      message.error(result.detail || 'CAD转换失败')
    }
  } catch (error) {
    console.error('CAD上传错误:', error)
    message.error('上传失败，请重试')
  }
  
  return false // 阻止默认上传行为
}

// 开始绘制
const startDrawing = () => {
  if (!props.floor) {
    message.warning('请先选择楼层')
    return
  }
  
  isDrawing.value = true
  drawingPoints.value = []
  showForm.value = false
  selectedSpace.value = null
  
  // 重置表单
  formData.value = {
    name: '',
    code: '',
    space_type: 'room',
    area_sqm: 0
  }
  
  emit('drawing-mode-change', true)
  message.info('开始在平面图上点击添加顶点')
}

// 取消绘制
const cancelDrawing = () => {
  isDrawing.value = false
  drawingPoints.value = []
  showForm.value = false
  emit('drawing-mode-change', false)
  message.info('已取消绘制')
}

// 添加顶点
const addPoint = (x: number, y: number) => {
  if (!isDrawing.value) return
  
  drawingPoints.value.push([x, y])
  message.success(`已添加顶点 ${drawingPoints.value.length}`)
}

// 完成绘制
const finishDrawing = () => {
  if (drawingPoints.value.length < 3) {
    message.warning('至少需要 3 个顶点')
    return
  }
  
  isDrawing.value = false
  showForm.value = true
  
  // 自动计算面积和生成建议编号
  calculateArea()
  generateSuggestedCode()
  
  emit('drawing-mode-change', false)
  message.success('绘制完成，请填写空间信息')
}

// 计算面积（简化版：包围盒面积）
const calculateArea = () => {
  const xs = drawingPoints.value.map(p => p[0])
  const ys = drawingPoints.value.map(p => p[1])
  
  const min_x = Math.min(...xs)
  const max_x = Math.max(...xs)
  const min_y = Math.min(...ys)
  const max_y = Math.max(...ys)
  
  // 假设 100px² = 1㎡
  formData.value.area_sqm = parseFloat(((max_x - min_x) * (max_y - min_y) / 100).toFixed(2))
}

// 生成建议编号
const generateSuggestedCode = () => {
  if (!props.floor) return
  
  const floorNum = props.floor.floor_number
  const existingCodes = props.spaces
    .filter(s => s.floor_id === props.floor?.id)
    .map(s => s.code)
  
  // 查找下一个可用编号
  let index = 1
  while (existingCodes.includes(`${floorNum}${String.fromCharCode(64 + index)}`)) {
    index++
  }
  
  formData.value.code = `${floorNum}${String.fromCharCode(64 + index)}`
  formData.value.name = `房间${formData.value.code}`
}

// 保存空间
const saveSpace = async () => {
  if (!props.floor || !canSave.value) return
  
  try {
    const response = await fetch('/api/space/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        floor_id: props.floor.id,
        space_type: formData.value.space_type,
        name: formData.value.name,
        code: formData.value.code,
        polygon: drawingPoints.value,
        area_sqm: formData.value.area_sqm
      })
    })
    
    const result = await response.json()
    
    if (result.code === 200) {
      message.success('空间创建成功')
      
      // 通知父组件
      emit('space-created', result.data)
      
      // 重置状态
      cancelDrawing()
    } else {
      message.error(result.message || '创建失败')
    }
  } catch (error) {
    console.error('创建空间失败:', error)
    message.error('网络错误，请重试')
  }
}

// 删除空间
const deleteSpace = async () => {
  if (!selectedSpace.value) return
  
  try {
    const response = await fetch(`/api/space/delete/${selectedSpace.value.id}`, {
      method: 'DELETE'
    })
    
    const result = await response.json()
    
    if (result.code === 200) {
      message.success('空间删除成功')
      emit('space-deleted', selectedSpace.value.id)
      selectedSpace.value = null
    } else {
      message.error(result.message || '删除失败')
    }
  } catch (error) {
    console.error('删除空间失败:', error)
    message.error('网络错误，请重试')
  }
}

// 选择空间进行编辑
const selectSpace = (space: Space) => {
  selectedSpace.value = space
  formData.value = {
    name: space.name,
    code: space.code,
    space_type: space.space_type,
    area_sqm: space.area_sqm
  }
  showForm.value = true
  // 确保类型正确
  drawingPoints.value = space.polygon.map((p: number[]) => [p[0], p[1]] as [number, number])
}

// 暴露方法给父组件
defineExpose({
  addPoint,
  finishDrawing,
  selectSpace,
  drawingPoints  // 暴露绘制点供父组件读取
})
</script>

<style scoped>
.space-editor {
  padding: 16px;
}
</style>
