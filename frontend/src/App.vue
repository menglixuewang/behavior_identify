<template>
  <div id="app">
    <el-container class="app-container">
      <!-- 侧边栏 -->
      <el-aside width="250px" class="sidebar">
        <div class="logo">
          <h2>智能行为检测系统</h2>
        </div>
        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/dashboard">
            <el-icon><House /></el-icon>
            <span>系统概览</span>
          </el-menu-item>
          <el-menu-item index="/upload">
            <el-icon><Upload /></el-icon>
            <span>视频上传</span>
          </el-menu-item>
          <el-menu-item index="/realtime">
            <el-icon><VideoCamera /></el-icon>
            <span>实时监控</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
          <el-menu-item index="/alerts">
            <el-icon><Warning /></el-icon>
            <span>报警记录</span>
          </el-menu-item>
          <el-menu-item index="/statistics">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据统计</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <!-- 顶部导航 -->
        <el-header class="header">
          <div class="header-content">
            <div class="header-left">
              <h3>{{ getPageTitle() }}</h3>
            </div>
            <div class="header-right">
              <el-badge :value="alertCount" class="alert-badge">
                <el-icon size="20"><Bell /></el-icon>
              </el-badge>
              <span class="system-status" :class="systemStatus">
                {{ systemStatus === 'online' ? '系统正常' : '系统异常' }}
              </span>
            </div>
          </div>
        </el-header>

        <!-- 页面内容 -->
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  House, Upload, VideoCamera, List, Warning, 
  DataAnalysis, Setting, Bell
} from '@element-plus/icons-vue'
import { checkHealth, getAlerts } from './utils/api.js'

export default {
  name: 'App',
  components: {
    House, Upload, VideoCamera, List, Warning, 
    DataAnalysis, Setting, Bell
  },
  setup() {
    const route = useRoute()
    const alertCount = ref(0)
    const systemStatus = ref('online')

    // 获取页面标题
    const getPageTitle = () => {
      const titleMap = {
        '/dashboard': '系统概览',
        '/upload': '视频上传',
        '/realtime': '实时监控',
        '/tasks': '任务管理',
        '/alerts': '报警记录',
        '/statistics': '数据统计',
        '/settings': '系统设置'
      }
      return titleMap[route.path] || '智能行为检测系统'
    }

    // 检查系统状态
    const checkSystemStatus = async () => {
      try {
        await checkHealth()
        systemStatus.value = 'online'
      } catch (error) {
        systemStatus.value = 'offline'
      }
    }

    // 获取报警数量
    const getAlertCount = async () => {
      try {
        const data = await getAlerts({ unread: true })
        alertCount.value = data.total || 0
      } catch (error) {
        console.error('获取报警数量失败:', error)
      }
    }

    onMounted(() => {
      checkSystemStatus()
      getAlertCount()
      
      // 定期检查系统状态
      setInterval(checkSystemStatus, 30000)
      setInterval(getAlertCount, 10000)
    })

    return {
      alertCount,
      systemStatus,
      getPageTitle
    }
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  overflow: hidden;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #434a50;
}

.logo h2 {
  color: #fff;
  margin: 0;
  font-size: 18px;
}

.sidebar-menu {
  border: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header-left h3 {
  margin: 0;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.alert-badge {
  cursor: pointer;
}

.system-status {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.system-status.online {
  background-color: #f0f9ff;
  color: #67c23a;
}

.system-status.offline {
  background-color: #fef0f0;
  color: #f56c6c;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}
</style> 