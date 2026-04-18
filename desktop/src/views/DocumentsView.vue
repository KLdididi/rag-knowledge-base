<template>
  <div class="documents-view">
    <header class="page-header">
      <h2>知识库管理</h2>
      <el-button type="primary" @click="showUploadDialog = true" :icon="Upload">
        上传文档
      </el-button>
    </header>
    
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="文档总数" :value="stats.totalDocs" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="向量数量" :value="stats.totalVectors" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="存储大小" :value="stats.storageSize" suffix="MB" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="最后更新" :value="stats.lastUpdate" />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 文档列表 -->
    <el-card class="documents-card">
      <template #header>
        <div class="card-header">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文档..."
            style="width: 300px"
            :prefix-icon="Search"
          />
          <el-button-group>
            <el-button @click="refreshDocuments" :icon="Refresh">刷新</el-button>
            <el-button type="danger" @click="deleteSelected" :disabled="!selectedDocs.length">
              删除选中
            </el-button>
          </el-button-group>
        </div>
      </template>
      
      <el-table
        :data="filteredDocuments"
        @selection-change="(rows: any[]) => selectedDocs = rows"
        v-loading="loading"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="{ row }">
            <el-icon><Document /></el-icon>
            {{ row.filename }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunks" label="分块数" width="100" />
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="uploadedAt" label="上传时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button text type="primary" @click="previewDocument(row)">预览</el-button>
            <el-button text type="danger" @click="deleteDocument(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="500px">
      <el-upload
        drag
        multiple
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="uploadFiles"
        accept=".pdf,.doc,.docx,.txt,.md"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF、Word、TXT、Markdown 格式，单个文件不超过 10MB
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="uploadDocuments" :loading="uploading">
          开始上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { invoke } from '@tauri-apps/api/tauri'

interface Document {
  id: string
  filename: string
  type: string
  chunks: number
  size: number
  uploadedAt: string
}

const loading = ref(false)
const uploading = ref(false)
const showUploadDialog = ref(false)
const searchQuery = ref('')
const documents = ref<Document[]>([])
const selectedDocs = ref<Document[]>([])
const uploadFiles = ref<any[]>([])

const stats = ref({
  totalDocs: 0,
  totalVectors: 0,
  storageSize: 0,
  lastUpdate: '-'
})

const filteredDocuments = computed(() => {
  if (!searchQuery.value) return documents.value
  return documents.value.filter(d => 
    d.filename.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const handleFileChange = (file: any, fileList: any[]) => {
  uploadFiles.value = fileList
}

const uploadDocuments = async () => {
  if (!uploadFiles.value.length) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  
  uploading.value = true
  try {
    await invoke('upload_documents', { files: uploadFiles.value })
    ElMessage.success('上传成功')
    showUploadDialog.value = false
    uploadFiles.value = []
    refreshDocuments()
  } catch (error) {
    ElMessage.error('上传失败: ' + error)
  } finally {
    uploading.value = false
  }
}

const refreshDocuments = async () => {
  loading.value = true
  try {
    const result = await invoke<{ documents: Document[]; stats: typeof stats.value }>('get_documents')
    documents.value = result.documents
    stats.value = result.stats
  } catch (error) {
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

const deleteDocument = async (doc: Document) => {
  await ElMessageBox.confirm('确定要删除此文档吗？', '确认删除', { type: 'warning' })
  await invoke('delete_document', { id: doc.id })
  ElMessage.success('删除成功')
  refreshDocuments()
}

const deleteSelected = async () => {
  await ElMessageBox.confirm(`确定要删除选中的 ${selectedDocs.value.length} 个文档吗？`, '确认删除', { type: 'warning' })
  await invoke('delete_documents', { ids: selectedDocs.value.map(d => d.id) })
  ElMessage.success('删除成功')
  refreshDocuments()
}

const previewDocument = async (doc: Document) => {
  // 打开预览
  const content = await invoke<string>('get_document_content', { id: doc.id })
  ElMessageBox.alert(content, doc.filename, { 
    customClass: 'document-preview',
    dangerouslyUseHTMLString: true
  })
}

onMounted(() => {
  refreshDocuments()
})
</script>

<style lang="scss" scoped>
.documents-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
  }
}

.stats-row {
  margin-bottom: 20px;
}

.documents-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
