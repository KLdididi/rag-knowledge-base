<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <el-icon :size="24"><Reading /></el-icon>
        <span class="logo-text">RAG 知识库</span>
      </div>
      
      <el-menu
        :default-active="currentRoute"
        class="sidebar-menu"
        router
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        
        <el-menu-item index="/documents">
          <el-icon><Document /></el-icon>
          <span>知识库</span>
        </el-menu-item>
        
        <el-menu-item index="/interview">
          <el-icon><User /></el-icon>
          <span>模拟面试</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <el-button text @click="openExternal('https://github.com/KLdididi/rag-knowledge-base')">
          <el-icon><Link /></el-icon>
          GitHub
        </el-button>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { open } from '@tauri-apps/api/shell'

const route = useRoute()
const currentRoute = computed(() => route.path)

const openExternal = (url: string) => {
  open(url)
}
</script>

<style lang="scss" scoped>
.main-layout {
  display: flex;
  height: 100%;
}

.sidebar {
  width: 220px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  
  .logo {
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid #e4e7ed;
    
    .logo-text {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .sidebar-menu {
    flex: 1;
    border-right: none;
    
    .el-menu-item {
      height: 50px;
      line-height: 50px;
      
      &.is-active {
        background: #ecf5ff;
      }
    }
  }
  
  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid #e4e7ed;
  }
}

.main-content {
  flex: 1;
  overflow: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
