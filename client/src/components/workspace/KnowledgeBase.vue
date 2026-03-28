<template>
  <div class="knowledge-base">
    <!-- 搜索和分类 -->
    <n-card
      :bordered="false"
      content-style="padding: 16px;"
      style="margin-bottom: 16px"
    >
      <n-space :size="16" justify="space-between">
        <n-space align="center">
          <n-input
            v-model:value="searchQuery"
            placeholder="搜索知识库..."
            clearable
            style="width: 400px"
          >
            <template #prefix>
              <n-icon :component="Search" />
            </template>
          </n-input>

          <!-- 文件上传组件 - 支持拖拽 -->
          <n-upload
            multiple
            :max="5"
            :show-file-list="true"
            :directory-dnd="true"
            :before-upload="handleBeforeUpload"
            @finish="handleUploadFinish"
            @error="handleUploadError"
            accept=".pdf,.txt,.doc,.docx"
            :trigger="uploadTrigger"
            action="/api/admin/upload"
          >
            <n-upload-dragger>
              <div style="margin-bottom: 12px">
                <n-icon :component="CloudUploadOutline" size="48" />
              </div>
              <n-text style="font-size: 14px">
                点击或拖拽文件到此处上传
              </n-text>
              <n-text depth="3" style="font-size: 12px; margin-top: 8px">
                支持 PDF、TXT、DOC、DOCX 格式，单个文件不超过 10MB
              </n-text>
            </n-upload-dragger>
          </n-upload>
        </n-space>

        <n-space>
          <n-select
            v-model:value="selectedCategory"
            :options="categoryOptions"
            placeholder="全部分类"
            clearable
            style="width: 150px"
          />

          <n-select
            v-model:value="selectedTag"
            :options="tagOptions"
            placeholder="全部标签"
            clearable
            style="width: 150px"
          />

          <n-button type="primary" @click="showAddModal = true">
            <template #icon>
              <n-icon :component="AddCircle" />
            </template>
            新增文档
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <!-- 知识卡片列表 -->
    <n-grid :cols="3" :x-gap="16" :y-gap="16">
      <n-grid-item v-for="doc in filteredDocuments" :key="doc.id">
        <n-card
          hoverable
          embedded
          @click="showDocumentDetail(doc)"
          style="cursor: pointer; height: 280px"
        >
          <template #header>
            <n-space vertical :size="8">
              <n-space align="center">
                <n-tag :type="getCategoryType(doc.category)" size="small">
                  {{ getCategoryName(doc.category) }}
                </n-tag>
                <n-text depth="3" style="font-size: 12px">{{
                  doc.created_at
                }}</n-text>
              </n-space>
              <h3 style="margin: 0; font-size: 16px">{{ doc.title }}</h3>
            </n-space>
          </template>

          <n-ellipsis
            :line-clamp="3"
            style="color: var(--text-secondary); font-size: 14px"
          >
            {{ doc.summary }}
          </n-ellipsis>

          <template #footer>
            <n-space justify="space-between" align="center">
              <n-space>
                <n-tag
                  v-for="tag in doc.tags.slice(0, 3)"
                  :key="tag"
                  size="small"
                  bordered
                >
                  {{ tag }}
                </n-tag>
              </n-space>
              <n-space align="center">
                <n-icon :component="Eye" size="16" />
                <span style="font-size: 12px">{{ doc.views }}</span>
                <n-button
                  text
                  type="error"
                  size="small"
                  @click.stop="handleDeleteDocument(doc)"
                >
                  <template #icon>
                    <n-icon :component="Trash" />
                  </template>
                </n-button>
              </n-space>
            </n-space>
          </template>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 空状态 -->
    <n-empty
      v-if="filteredDocuments.length === 0"
      description="暂无相关文档"
      style="margin-top: 60px"
    />

    <!-- 文档详情弹窗 -->
    <n-modal
      v-model:show="showDetailModal"
      preset="card"
      title="文档详情"
      style="width: 900px; max-height: 80vh; overflow-y: auto"
    >
      <n-space vertical :size="16" v-if="currentDoc">
        <n-space align="center">
          <n-tag :type="getCategoryType(currentDoc.category)">
            {{ getCategoryName(currentDoc.category) }}
          </n-tag>
          <n-text depth="3">{{ currentDoc.created_at }}</n-text>
          <n-text depth="3">浏览 {{ currentDoc.views }}次</n-text>
        </n-space>

        <n-divider />

        <h2 style="margin: 0">{{ currentDoc.title }}</h2>

        <n-divider />

        <div style="line-height: 1.8; color: var(--text-primary)">
          <h3>问题描述</h3>
          <p>{{ currentDoc.description }}</p>

          <h3>解决方案</h3>
          <p>{{ currentDoc.solution }}</p>

          <h3>注意事项</h3>
          <ul>
            <li v-for="(item, index) in currentDoc.notes" :key="index">
              {{ item }}
            </li>
          </ul>
        </div>

        <n-divider />

        <n-space justify="space-between">
          <n-space>
            <n-tag
              v-for="tag in currentDoc.tags"
              :key="tag"
              size="large"
              bordered
            >
              {{ tag }}
            </n-tag>
          </n-space>

          <n-space>
            <n-button @click="handleCopy(currentDoc)">复制内容</n-button>
            <n-button type="primary">打印文档</n-button>
            <n-button 
              type="error" 
              ghost
              @click="handleDeleteDocument(currentDoc)"
            >
              删除文档
            </n-button>
          </n-space>
        </n-space>
      </n-space>
    </n-modal>

    <!-- 新增文档弹窗 -->
    <n-modal
      v-model:show="showAddModal"
      preset="card"
      title="新增文档"
      style="width: 800px"
    >
      <n-form
        ref="addDocFormRef"
        :model="addDocForm"
        :rules="addDocRules"
        label-placement="left"
        label-width="100px"
      >
        <n-form-item label="文档标题" path="title">
          <n-input v-model:value="addDocForm.title" placeholder="请输入标题" />
        </n-form-item>

        <n-form-item label="所属分类" path="category">
          <n-select
            v-model:value="addDocForm.category"
            :options="categoryOptions"
            placeholder="请选择分类"
          />
        </n-form-item>

        <n-form-item label="标签">
          <n-select
            v-model:value="addDocForm.tags"
            :options="tagOptions"
            placeholder="选择标签（可多选）"
            multiple
          />
        </n-form-item>

        <n-form-item label="摘要" path="summary">
          <n-input
            v-model:value="addDocForm.summary"
            type="textarea"
            placeholder="简要描述文档内容"
            :rows="2"
          />
        </n-form-item>

        <n-form-item label="问题描述" path="description">
          <n-input
            v-model:value="addDocForm.description"
            type="textarea"
            placeholder="详细描述问题现象"
            :rows="4"
          />
        </n-form-item>

        <n-form-item label="解决方案" path="solution">
          <n-input
            v-model:value="addDocForm.solution"
            type="textarea"
            placeholder="详细解决步骤"
            :rows="6"
          />
        </n-form-item>

        <n-form-item label="注意事项">
          <n-dynamic-tags v-model:value="addDocForm.notes" />
        </n-form-item>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button
            type="primary"
            @click="handleAddDocument"
            :loading="addingDoc"
          >
            确定
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, h } from "vue";
import { Search, AddCircle, Eye, DocumentText, Trash } from "@vicons/ionicons5";
import { CloudUploadOutline } from "@vicons/ionicons5";
import { NTag, NIcon, NButton, useMessage, useDialog } from "naive-ui";
import type { UploadFileInfo } from "naive-ui";
import { uploadDocument } from "@/api/analysis";
import { 
  addDocument, 
  getKnowledgeList, 
  getKnowledgeDetail,
  deleteKnowledgeDocument,
  type KnowledgeDocument as ApiKnowledgeDocument,
  type AddDocumentParams 
} from "@/api/admin";

// 本地 Document 类型（直接使用 API 返回的字段）
interface Document extends ApiKnowledgeDocument {
  description: string;
  solution: string;
  notes: string[];
}

interface UploadFileRecord {
  name: string;
  savedName: string;
  uploadTime: string;
  blocksIndexed: number;
}

const message = useMessage();
const dialog = useDialog();

// 搜索和筛选
const searchQuery = ref("");
const selectedCategory = ref("");
const selectedTag = ref("");

// 分类选项
const categoryOptions = [
  { label: "运维技巧", value: "skill", color: "info" },
  { label: "故障案例", value: "case", color: "warning" },
  { label: "保养方案", value: "maintenance", color: "success" },
  { label: "操作规范", value: "standard", color: "error" },
  { label: "技术文档", value: "technical", color: "default" },
];

// 标签选项
const tagOptions = [
  { label: "空调系统", value: "hvac" },
  { label: "电气系统", value: "electrical" },
  { label: "给排水", value: "plumbing" },
  { label: "消防系统", value: "fire" },
  { label: "电梯", value: "elevator" },
  { label: "节能改造", value: "energy-saving" },
  { label: "预防性维护", value: "preventive" },
  { label: "应急处理", value: "emergency" },
];

// Mock 文档数据 - 仅用于初始展示，实际数据从 API 加载
const documents = ref<Document[]>([]);

// 过滤后的文档
const filteredDocuments = computed(() => {
  return documents.value.filter((doc) => {
    if (selectedCategory.value && doc.category !== selectedCategory.value)
      return false;
    if (selectedTag.value && !doc.tags.includes(selectedTag.value))
      return false;
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      return (
        doc.title.toLowerCase().includes(query) ||
        doc.summary.toLowerCase().includes(query) ||
        doc.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }
    return true;
  });
});

// 详情展示
const showDetailModal = ref(false);
const currentDoc = ref<Document | null>(null);

// 新增文档
const showAddModal = ref(false);
const addingDoc = ref(false);
const addDocFormRef = ref<any>(null);
const addDocForm = reactive({
  title: "",
  category: "",
  tags: [],
  summary: "",
  description: "",
  solution: "",
  notes: [] as string[],
});

const addDocRules = {
  title: { required: true, message: "请输入文档标题", trigger: "blur" },
  category: { required: true, message: "请选择分类", trigger: "change" },
  summary: { required: true, message: "请输入摘要", trigger: "blur" },
  description: { required: true, message: "请输入问题描述", trigger: "blur" },
  solution: { required: true, message: "请输入解决方案", trigger: "blur" },
};

function uploadTrigger(){
  addDocFormRef.value.validate();
}

// 辅助函数
function getCategoryType(
  category: string,
): "default" | "info" | "warning" | "success" | "error" {
  const map: Record<
    string,
    "default" | "info" | "warning" | "success" | "error"
  > = {
    skill: "info",
    case: "warning",
    maintenance: "success",
    standard: "error",
    technical: "default",
  };
  return map[category] || "default";
}

function getCategoryName(category: string): string {
  const option = categoryOptions.find((o) => o.value === category);
  return option?.label || category;
}

// 事件处理
const showDocumentDetail = async (doc: Document) => {
  currentDoc.value = doc;
  showDetailModal.value = true;

  // 增加浏览量 - 调用 API 更新
  try {
    await getKnowledgeDetail(doc.id);
  } catch (error) {
    console.error('更新浏览量失败:', error);
  }
};

const handleCopy = (doc: Document) => {
  const text = `${doc.title}\n\n问题描述：${doc.description}\n\n解决方案：${doc.solution}`;
  navigator.clipboard.writeText(text);
  message.success("内容已复制到剪贴板");
};

const handleDeleteDocument = async (doc: Document) => {
  // 显示确认对话框
  const confirmed = await new Promise<boolean>((resolve) => {
    dialog.warning({
      title: '确认删除',
      content: `确定要删除文档"${doc.title}"吗？此操作不可恢复。`,
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
      onMaskClick: () => resolve(false),
    });
  });

  if (!confirmed) return;

  try {
    const response = await deleteKnowledgeDocument(doc.id);
    
    if (response.data.code === 200 && response.data.data?.is_success) {
      message.success('文档删除成功');
      // 刷新文档列表
      await fetchDocuments();
      // 如果正在查看详情，关闭弹窗
      showDetailModal.value = false;
    } else {
      throw new Error(response.data.message || '删除失败');
    }
  } catch (error: any) {
    console.error('[KnowledgeBase] 删除文档失败:', error);
    message.error(error.response?.data?.message || '删除失败，请稍后重试');
  }
};

const handleAddDocument = async () => {
  try {
    await addDocFormRef.value?.validate();
    addingDoc.value = true;

    const documentData: AddDocumentParams = {
      title: addDocForm.title,
      category: addDocForm.category,
      tags: addDocForm.tags,
      summary: addDocForm.summary,
      description: addDocForm.description,
      solution: addDocForm.solution,
      notes: addDocForm.notes,
    };

    const response = await addDocument(documentData);
    
    if (response.data.code === 200) {
      message.success("文档添加成功");
      showAddModal.value = false;
      
      // 重置表单
      Object.assign(addDocForm, {
        title: "",
        category: "",
        tags: [],
        summary: "",
        description: "",
        solution: "",
        notes: [],
      });
      
      // 刷新文档列表
      await fetchDocuments();
    } else {
      throw new Error(response.data.message || '保存失败');
    }
  } catch (error: any) {
    console.error('[KnowledgeBase] 添加文档失败:', error);
    message.error(error.response?.data?.message || '添加失败，请稍后重试');
  } finally {
    addingDoc.value = false;
  }
};

// 文件上传事件处理
const uploading = ref(false);
const uploadedFiles = ref<UploadFileRecord[]>([]);

const handleBeforeUpload = ({ file }: { file: UploadFileInfo }) => {
  const validTypes = [
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ];
  const validExtensions = [".pdf", ".txt", ".doc", ".docx"];

  const hasValidExtension = validExtensions.some((ext) =>
    file.name.toLowerCase().endsWith(ext),
  );

  if (!hasValidExtension) {
    message.error("只支持 PDF、TXT、DOC、DOCX 格式的文件");
    return false;
  }

  if (file.file && file.file.size > 10 * 1024 * 1024) {
    message.error("文件大小不能超过 10MB");
    return false;
  }

  return true;
};

const handleUploadFinish = ({ file, event }: { file: UploadFileInfo, event?: ProgressEvent }) => {
  if (!file.file) {
    message.error("文件无效");
    return;
  }

  uploading.value = true;

  // 使用 IIFE 包裹异步逻辑
  (async () => {
    try {
      const formData = new FormData();
      formData.append('file', file.file!);
      
      const response = await fetch('/api/admin/upload', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      
      if (result.code === 200 && result.data.success) {
        message.success(`✅ "${file.name}" 上传成功！${result.data.message}`);
        
        // 记录上传的文件
        uploadedFiles.value.push({
          name: file.name,
          savedName: result.data.saved_filename,
          uploadTime: new Date().toLocaleString('zh-CN'),
          blocksIndexed: result.data.stats?.blocks_indexed || 0
        });

        // 上传成功后创建文档记录（调用知识库 API）
        const documentData: AddDocumentParams = {
          title: file.name.replace(/\.[^/.]+$/, ""), // 去掉文件扩展名作为标题
          category: 'technical', // 默认分类为技术文档
          tags: [], // 初始标签为空
          summary: `上传文件：${file.name}`,
          description: `文件 ${file.name} 已上传至知识库，共建立 ${result.data.stats?.blocks_indexed || 0} 个文本块索引。`,
          solution: "可通过 AI 助手检索此文档内容",
          notes: [`原始文件名：${file.name}`, `保存路径：${result.data.saved_filename}`],
        };

        // 调用知识库 API 保存文档记录
        await addDocument(documentData);
        message.success("📄 文档记录已创建");

        // 刷新文档列表
        await fetchDocuments();
      } else {
        throw new Error(result.message || "上传失败");
      }
    } catch (error: any) {
      console.error('上传错误:', error);
      message.error(`❌ 上传失败：${error.message}`);
    } finally {
      uploading.value = false;
    }
  })();
};

const handleUploadError = ({ file }: { file: UploadFileInfo }) => {
  message.error(`文件 "${file.name}" 上传失败`);
  uploading.value = false;
};

const fetchDocuments = async () => {
  try {
    const response = await getKnowledgeList({
      category: selectedCategory.value || undefined,
      keyword: searchQuery.value || undefined,
      tag: selectedTag.value || undefined,
    });
    
    // 直接使用后端返回的数据，不做转换
    if (response.data.code === 200 && response.data.data?.items) {
      documents.value = response.data.data.items as Document[];
    } else {
      throw new Error(response.data.message || '获取失败');
    }
  } catch (error) {
    console.error("[KnowledgeBase] 获取文档列表失败", error);
    message.error('获取文档列表失败');
  }
};

// 监听筛选条件变化
watch([selectedCategory, selectedTag, searchQuery], () => {
  fetchDocuments();
});

// 组件挂载时加载数据
onMounted(() => {
  fetchDocuments();
});
</script>

<style scoped>
.knowledge-base {
  min-height: 100%;
}

/* 拖拽区域样式优化 */
:deep(.n-upload-dragger) {
  padding: 24px 16px;
  border: 2px dashed var(--n-border-color);
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.n-upload-dragger:hover) {
  border-color: var(--n-color-target);
  background-color: var(--n-color-hover);
}

:deep(.n-upload-dragger.n-upload-dragger--active) {
  border-color: var(--n-color-target);
  background-color: var(--n-color-hover);
}
</style>