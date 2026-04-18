<template>
  <div class="interview-view">
    <header class="page-header">
      <h2>模拟面试</h2>
      <el-button type="primary" @click="startNewInterview" :icon="VideoCamera">
        开始面试
      </el-button>
    </header>
    
    <el-row :gutter="20">
      <!-- 面试配置 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>面试配置</span>
          </template>
          
          <el-form :model="interviewConfig" label-width="100px">
            <el-form-item label="目标岗位">
              <el-input v-model="interviewConfig.position" placeholder="如：后端工程师" />
            </el-form-item>
            
            <el-form-item label="目标公司">
              <el-select v-model="interviewConfig.companies" multiple filterable allow-create placeholder="选择或输入公司">
                <el-option label="字节跳动" value="字节跳动" />
                <el-option label="腾讯" value="腾讯" />
                <el-option label="阿里巴巴" value="阿里巴巴" />
                <el-option label="美团" value="美团" />
                <el-option label="京东" value="京东" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="题目难度">
              <el-slider v-model="interviewConfig.difficulty" :min="1" :max="4" :marks="difficultyMarks" />
            </el-form-item>
            
            <el-form-item label="题目数量">
              <el-input-number v-model="interviewConfig.count" :min="3" :max="20" />
            </el-form-item>
          </el-form>
          
          <el-button type="primary" block @click="startNewInterview" :loading="starting">
            开始面试
          </el-button>
        </el-card>
        
        <!-- 历史记录 -->
        <el-card style="margin-top: 16px">
          <template #header>
            <span>历史记录</span>
          </template>
          
          <el-timeline>
            <el-timeline-item
              v-for="record in historyRecords"
              :key="record.id"
              :timestamp="record.date"
              placement="top"
            >
              <el-card shadow="hover" @click="viewRecord(record)" style="cursor: pointer">
                <p><strong>{{ record.position }}</strong></p>
                <p>得分: {{ record.score }}分</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
      
      <!-- 面试进行区 -->
      <el-col :span="16">
        <el-card v-if="!currentSession" class="empty-state">
          <el-empty description="点击「开始面试」开始练习">
            <el-button type="primary" @click="startNewInterview">立即开始</el-button>
          </el-empty>
        </el-card>
        
        <el-card v-else class="interview-session">
          <template #header>
            <div class="session-header">
              <span>面试进行中</span>
              <el-tag type="warning">进度: {{ currentSession.progress }}</el-tag>
            </div>
          </template>
          
          <!-- 当前题目 -->
          <div class="current-question">
            <div class="question-meta">
              <el-tag>{{ currentSession.currentQuestion?.category }}</el-tag>
              <el-rate v-model="currentSession.currentQuestion?.difficulty" disabled />
            </div>
            <h3>{{ currentSession.currentQuestion?.question }}</h3>
            <p class="hint">预计回答时间: {{ currentSession.currentQuestion?.estimatedTime }} 分钟</p>
          </div>
          
          <!-- 回答输入 -->
          <el-input
            v-model="currentAnswer"
            type="textarea"
            :rows="6"
            placeholder="请输入你的回答..."
          />
          
          <div class="actions">
            <el-button @click="skipQuestion">跳过此题</el-button>
            <el-button type="primary" @click="submitAnswer" :loading="submitting">
              提交回答
            </el-button>
          </div>
          
          <!-- 反馈 -->
          <div v-if="lastFeedback" class="feedback">
            <el-alert
              :title="`得分: ${lastFeedback.score}分`"
              :type="lastFeedback.score >= 70 ? 'success' : lastFeedback.score >= 50 ? 'warning' : 'error'"
              show-icon
            >
              <p>{{ lastFeedback.feedback }}</p>
            </el-alert>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 面试报告对话框 -->
    <el-dialog v-model="showReport" title="面试报告" width="600px">
      <div class="report">
        <el-result
          :icon="reportData.score >= 70 ? 'success' : reportData.score >= 50 ? 'warning' : 'error'"
          :title="`总分: ${reportData.score}分`"
          :sub-title="reportData.comment"
        />
        
        <el-divider />
        
        <h4>分类得分</h4>
        <el-progress
          v-for="(score, category) in reportData.categoryScores"
          :key="category"
          :percentage="score"
          :status="score >= 70 ? 'success' : score >= 50 ? 'warning' : 'exception'"
        >
          <span>{{ category }}</span>
        </el-progress>
        
        <el-divider />
        
        <h4>改进建议</h4>
        <ul>
          <li v-for="(rec, idx) in reportData.recommendations" :key="idx">{{ rec }}</li>
        </ul>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { invoke } from '@tauri-apps/api/tauri'

const starting = ref(false)
const submitting = ref(false)
const showReport = ref(false)
const currentSession = ref<any>(null)
const currentAnswer = ref('')
const lastFeedback = ref<any>(null)

const interviewConfig = ref({
  position: '',
  companies: [] as string[],
  difficulty: 2,
  count: 5
})

const difficultyMarks = {
  1: '简单',
  2: '中等',
  3: '困难',
  4: '专家'
}

const historyRecords = ref<any[]>([])
const reportData = ref({
  score: 0,
  comment: '',
  categoryScores: {} as Record<string, number>,
  recommendations: [] as string[]
})

const startNewInterview = async () => {
  if (!interviewConfig.value.position) {
    ElMessage.warning('请输入目标岗位')
    return
  }
  
  starting.value = true
  try {
    const session = await invoke('start_interview', {
      position: interviewConfig.value.position,
      companies: interviewConfig.value.companies,
      difficulty: interviewConfig.value.difficulty,
      count: interviewConfig.value.count
    })
    currentSession.value = session
    currentAnswer.value = ''
    lastFeedback.value = null
  } catch (error) {
    ElMessage.error('启动面试失败: ' + error)
  } finally {
    starting.value = false
  }
}

const submitAnswer = async () => {
  if (!currentAnswer.value.trim()) {
    ElMessage.warning('请输入你的回答')
    return
  }
  
  submitting.value = true
  try {
    const result = await invoke('submit_interview_answer', {
      sessionId: currentSession.value.id,
      questionId: currentSession.value.currentQuestion.id,
      answer: currentAnswer.value
    })
    
    lastFeedback.value = result.evaluation
    
    if (result.nextQuestion) {
      currentSession.value.currentQuestion = result.nextQuestion
      currentSession.value.progress = result.progress
      currentAnswer.value = ''
    } else {
      // 面试结束，显示报告
      const report = await invoke('complete_interview', {
        sessionId: currentSession.value.id
      })
      reportData.value = report
      showReport.value = true
      currentSession.value = null
      loadHistory()
    }
  } catch (error) {
    ElMessage.error('提交失败: ' + error)
  } finally {
    submitting.value = false
  }
}

const skipQuestion = async () => {
  currentAnswer.value = ''
  // 获取下一题
}

const viewRecord = (record: any) => {
  // 查看历史记录详情
}

const loadHistory = async () => {
  try {
    const records = await invoke('get_interview_history')
    historyRecords.value = records
  } catch (error) {
    console.error('加载历史记录失败', error)
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style lang="scss" scoped>
.interview-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 { margin: 0; }
}

.empty-state {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.interview-session {
  .session-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .current-question {
    padding: 20px;
    background: #f5f7fa;
    border-radius: 8px;
    margin-bottom: 20px;
    
    .question-meta {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }
    
    h3 { margin: 0 0 8px; }
    
    .hint {
      color: #909399;
      font-size: 13px;
      margin: 0;
    }
  }
  
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 16px;
  }
  
  .feedback {
    margin-top: 20px;
  }
}

.report {
  h4 {
    margin: 16px 0 12px;
  }
  
  ul {
    padding-left: 20px;
  }
}
</style>
