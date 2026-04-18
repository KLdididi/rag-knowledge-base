<template>
  <div class="chat-view">
    <!-- 头部 -->
    <header class="chat-header">
      <h2>智能问答</h2>
      <div class="header-actions">
        <el-select v-model="selectedModel" size="small" style="width: 150px">
          <el-option label="Qwen2.5 3B" value="qwen2.5:3b" />
          <el-option label="Llama3 8B" value="llama3" />
        </el-select>
        <el-button @click="clearChat" :icon="Delete">清空对话</el-button>
      </div>
    </header>
    
    <!-- 对话区域 -->
    <div class="chat-messages" ref="messagesContainer">
      <div 
        v-for="(msg, idx) in messages" 
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="message-avatar">
          <el-avatar v-if="msg.role === 'user'" :icon="UserFilled" />
          <el-avatar v-else :icon="ChatDotRound" />
        </div>
        <div class="message-content">
          <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          <div class="message-time">{{ msg.time }}</div>
        </div>
      </div>
      
      <div v-if="loading" class="message assistant loading">
        <div class="message-avatar">
          <el-avatar :icon="ChatDotRound" />
        </div>
        <div class="message-content">
          <el-icon class="is-loading"><Loading /></el-icon>
          正在思考中...
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="chat-input">
      <el-input
        v-model="userInput"
        type="textarea"
        :rows="3"
        placeholder="输入你的问题，按 Enter 发送，Shift+Enter 换行"
        @keydown.enter.exact.prevent="sendMessage"
        @keydown.enter.shift.exact="() => {}"
      />
      <div class="input-actions">
        <el-checkbox v-model="useRAG">使用知识库增强</el-checkbox>
        <el-button type="primary" @click="sendMessage" :loading="loading">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { invoke } from '@tauri-apps/api/tauri'

interface Message {
  role: 'user' | 'assistant'
  content: string
  time: string
}

const messages = ref<Message[]>([])
const userInput = ref('')
const loading = ref(false)
const selectedModel = ref('qwen2.5:3b')
const useRAG = ref(true)
const messagesContainer = ref<HTMLElement>()

const renderMarkdown = (text: string) => {
  return marked(text)
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!userInput.value.trim()) return
  
  const question = userInput.value.trim()
  userInput.value = ''
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: question,
    time: new Date().toLocaleTimeString()
  })
  scrollToBottom()
  
  loading.value = true
  
  try {
    // 调用后端 API
    const response = await invoke<{ answer: string; sources?: string[] }>('query_rag', {
      question,
      model: selectedModel.value,
      useRag: useRAG.value
    })
    
    let answer = response.answer
    if (response.sources && response.sources.length > 0) {
      answer += '\n\n---\n**参考来源:**\n'
      response.sources.forEach((s, i) => {
        answer += `${i + 1}. ${s}\n`
      })
    }
    
    messages.value.push({
      role: 'assistant',
      content: answer,
      time: new Date().toLocaleTimeString()
    })
  } catch (error) {
    ElMessage.error('查询失败: ' + error)
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const clearChat = () => {
  messages.value = []
}

onMounted(() => {
  // 欢迎消息
  messages.value.push({
    role: 'assistant',
    content: '你好！我是 RAG 知识库问答助手。你可以向我提问，我会基于知识库内容为你解答。\n\n你可以：\n- 上传文档到知识库\n- 开启/关闭知识库增强模式\n- 进行模拟面试练习',
    time: new Date().toLocaleTimeString()
  })
})
</script>

<style lang="scss" scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
    font-size: 20px;
  }
  
  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 16px;
  
  .message {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    
    &.user {
      flex-direction: row-reverse;
      
      .message-content {
        background: #409eff;
        color: #fff;
      }
    }
    
    &.assistant {
      .message-content {
        background: #f4f4f5;
      }
    }
    
    &.loading {
      .message-content {
        color: #909399;
      }
    }
    
    .message-avatar {
      flex-shrink: 0;
    }
    
    .message-content {
      max-width: 70%;
      padding: 12px 16px;
      border-radius: 12px;
      
      .message-text {
        line-height: 1.6;
        
        :deep(pre) {
          background: #282c34;
          color: #abb2bf;
          padding: 12px;
          border-radius: 4px;
          overflow-x: auto;
        }
        
        :deep(code) {
          background: #f4f4f5;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Consolas', monospace;
        }
      }
      
      .message-time {
        font-size: 12px;
        color: #909399;
        margin-top: 8px;
        text-align: right;
      }
    }
  }
}

.chat-input {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  
  .input-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
  }
}
</style>
