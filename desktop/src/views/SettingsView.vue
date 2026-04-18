<template>
  <div class="settings-view">
    <el-row :gutter="20">
      <!-- 基础设置 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>基础设置</span>
          </template>
          
          <el-form :model="settings" label-width="120px">
            <el-form-item label="Ollama 地址">
              <el-input v-model="settings.ollamaHost" placeholder="http://localhost:11434" />
            </el-form-item>
            
            <el-form-item label="默认模型">
              <el-select v-model="settings.defaultModel">
                <el-option label="Qwen2.5 3B" value="qwen2.5:3b" />
                <el-option label="Llama3 8B" value="llama3" />
                <el-option label="Llama3 70B" value="llama3:70b" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="Embedding 模型">
              <el-select v-model="settings.embeddingModel">
                <el-option label="nomic-embed-text" value="nomic-embed-text" />
                <el-option label="mxbai-embed-large" value="mxbai-embed-large" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="检索数量">
              <el-input-number v-model="settings.topK" :min="1" :max="20" />
            </el-form-item>
            
            <el-form-item label="温度参数">
              <el-slider v-model="settings.temperature" :min="0" :max="1" :step="0.1" show-input />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 高级设置 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>高级设置</span>
          </template>
          
          <el-form :model="settings" label-width="120px">
            <el-form-item label="分块大小">
              <el-input-number v-model="settings.chunkSize" :min="100" :max="2000" :step="100" />
            </el-form-item>
            
            <el-form-item label="分块重叠">
              <el-input-number v-model="settings.chunkOverlap" :min="0" :max="500" :step="50" />
            </el-form-item>
            
            <el-form-item label="启用缓存">
              <el-switch v-model="settings.enableCache" />
            </el-form-item>
            
            <el-form-item label="缓存 TTL">
              <el-input-number v-model="settings.cacheTTL" :min="60" :max="86400" />
              <span style="margin-left: 8px; color: #909399;">秒</span>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 系统状态 -->
        <el-card style="margin-top: 16px">
          <template #header>
            <span>系统状态</span>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="版本">
              {{ systemInfo.version }}
            </el-descriptions-item>
            <el-descriptions-item label="数据库">
              <el-tag :type="systemInfo.dbStatus === '正常' ? 'success' : 'danger'">
                {{ systemInfo.dbStatus }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Ollama">
              <el-tag :type="systemInfo.ollamaStatus === '已连接' ? 'success' : 'danger'">
                {{ systemInfo.ollamaStatus }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="已加载模型">
              {{ systemInfo.loadedModels }}
            </el-descriptions-item>
          </el-descriptions>
          
          <div style="margin-top: 16px; display: flex; gap: 12px;">
            <el-button @click="checkOllama" :loading="checking">检测连接</el-button>
            <el-button @click="openDataFolder">打开数据目录</el-button>
            <el-button type="danger" @click="clearCache">清空缓存</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <div class="actions">
      <el-button type="primary" @click="saveSettings" :loading="saving">保存设置</el-button>
      <el-button @click="resetSettings">恢复默认</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { invoke } from '@tauri-apps/api/tauri'
import { open } from '@tauri-apps/api/shell'
import { appDataDir } from '@tauri-apps/api/path'

const saving = ref(false)
const checking = ref(false)

const settings = reactive({
  ollamaHost: 'http://localhost:11434',
  defaultModel: 'qwen2.5:3b',
  embeddingModel: 'nomic-embed-text',
  topK: 5,
  temperature: 0.7,
  chunkSize: 1000,
  chunkOverlap: 200,
  enableCache: true,
  cacheTTL: 3600
})

const systemInfo = reactive({
  version: '1.0.0',
  dbStatus: '检测中...',
  ollamaStatus: '检测中...',
  loadedModels: '-'
})

const loadSettings = async () => {
  try {
    const saved = await invoke('get_settings')
    Object.assign(settings, saved)
  } catch (error) {
    console.error('加载设置失败', error)
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await invoke('save_settings', { settings })
    ElMessage.success('设置已保存')
  } catch (error) {
    ElMessage.error('保存失败: ' + error)
  } finally {
    saving.value = false
  }
}

const resetSettings = async () => {
  await ElMessageBox.confirm('确定要恢复默认设置吗？', '确认', { type: 'warning' })
  // 恢复默认值
  settings.ollamaHost = 'http://localhost:11434'
  settings.defaultModel = 'qwen2.5:3b'
  settings.topK = 5
  settings.temperature = 0.7
  ElMessage.success('已恢复默认设置')
}

const checkOllama = async () => {
  checking.value = true
  try {
    const result = await invoke('check_ollama', { host: settings.ollamaHost })
    systemInfo.ollamaStatus = '已连接'
    systemInfo.loadedModels = result.models?.join(', ') || '-'
  } catch (error) {
    systemInfo.ollamaStatus = '连接失败'
    systemInfo.loadedModels = '-'
  } finally {
    checking.value = false
  }
}

const openDataFolder = async () => {
  const dataDir = await appDataDir()
  open(dataDir)
}

const clearCache = async () => {
  await ElMessageBox.confirm('确定要清空缓存吗？这将清除所有问答缓存。', '确认', { type: 'warning' })
  await invoke('clear_cache')
  ElMessage.success('缓存已清空')
}

onMounted(() => {
  loadSettings()
  checkOllama()
  systemInfo.dbStatus = '正常'
})
</script>

<style lang="scss" scoped>
.settings-view {
  padding: 20px;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}
</style>
