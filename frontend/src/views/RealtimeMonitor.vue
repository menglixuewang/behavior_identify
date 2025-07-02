<template>
  <div class="realtime-monitor">
    <!-- 控制面板 -->
    <el-card class="control-panel">
      <template #header>
        <div class="panel-header">
          <span>实时监控控制台</span>
          <div class="control-buttons">
            <el-button 
              v-if="!isMonitoring" 
              type="primary" 
              @click="startMonitoring"
            >
              <el-icon><VideoCamera /></el-icon>
              开始监控
            </el-button>
            <el-button 
              v-else 
              type="danger" 
              @click="stopMonitoring"
            >
              <el-icon><VideoPause /></el-icon>
              停止监控
            </el-button>
            <el-button @click="showSettings = true">
              <el-icon><Setting /></el-icon>
              设置
            </el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="20" class="control-row">
        <el-col :span="6">
          <el-form-item label="视频源">
            <el-select v-model="monitorConfig.source" :disabled="isMonitoring">
              <el-option label="摄像头" value="camera" />
              <el-option label="RTSP流" value="rtsp" />
              <el-option label="本地文件" value="file" />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="6">
          <el-form-item label="检测模式">
            <el-select v-model="monitorConfig.mode" :disabled="isMonitoring">
              <el-option label="实时检测" value="realtime" />
              <el-option label="仅预览" value="preview" />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="6">
          <el-form-item label="录制">
            <el-switch 
              v-model="monitorConfig.recording" 
              :disabled="!isMonitoring"
              active-text="录制中" 
              inactive-text="不录制"
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="6">
          <el-form-item label="报警">
            <el-switch 
              v-model="monitorConfig.alertEnabled" 
              active-text="启用" 
              inactive-text="禁用"
            />
          </el-form-item>
        </el-col>
      </el-row>
    </el-card>

    <!-- 监控主界面 -->
    <el-row :gutter="20" class="monitor-main">
      <!-- 视频显示区域 -->
      <el-col :span="16">
        <el-card class="video-card">
          <template #header>
            <div class="video-header">
              <span>实时画面</span>
              <div class="video-controls">
                <el-tag
                  :type="isMonitoring ? 'success' : 'info'"
                  size="small"
                >
                  {{ isMonitoring ? '监控中' : '已停止' }}
                </el-tag>
                <span v-if="isMonitoring" class="fps-indicator">
                  {{ currentFPS }} FPS
                </span>
              </div>
            </div>
          </template>

          <div class="video-container">
            <div v-if="!isMonitoring" class="video-placeholder">
              <el-icon size="64"><VideoCamera /></el-icon>
              <p>点击开始监控</p>
            </div>
            
            <div v-else class="video-display">
              <img
                :src="videoStreamUrl"
                class="video-stream"
                alt="Real-time video stream"
                @error="handleStreamError"
              />

              <!-- 检测信息覆盖层 -->
              <div class="detection-overlay">
                <div class="detection-info">
                  <div class="info-item">
                    <span class="label">检测对象:</span>
                    <span class="value">{{ currentDetections.length }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">处理时间:</span>
                    <span class="value">{{ processingTime }}ms</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 侧边信息面板 -->
      <el-col :span="8">
        <!-- 实时检测结果 -->
        <el-card class="detection-card">
          <template #header>
            <span>实时检测</span>
          </template>
          
          <div class="detection-list">
            <div 
              v-for="detection in currentDetections" 
              :key="detection.id"
              class="detection-item"
              :class="{ 'alert': detection.isAlert }"
            >
              <div class="detection-icon">
                <el-icon v-if="detection.isAlert"><Warning /></el-icon>
                <el-icon v-else><User /></el-icon>
              </div>
              <div class="detection-content">
                <div class="detection-behavior">{{ detection.behavior }}</div>
                <div class="detection-confidence">
                  置信度: {{ (detection.confidence * 100).toFixed(1) }}%
                </div>
              </div>
            </div>
            
            <div v-if="currentDetections.length === 0" class="no-detections">
              <el-icon size="32"><Search /></el-icon>
              <p>暂无检测结果</p>
            </div>
          </div>
        </el-card>

        <!-- 报警记录 -->
        <el-card class="alert-card">
          <template #header>
            <div class="card-header">
              <span>实时报警</span>
              <el-badge :value="realtimeAlerts.length" :max="99" />
            </div>
          </template>
          
          <div class="alert-list">
            <div 
              v-for="alert in realtimeAlerts.slice(0, 5)" 
              :key="alert.id"
              class="alert-item"
              :class="alert.level"
            >
              <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
              <div class="alert-behavior">{{ alert.behavior }}</div>
              <div class="alert-confidence">{{ (alert.confidence * 100).toFixed(1) }}%</div>
            </div>
            
            <div v-if="realtimeAlerts.length === 0" class="no-alerts">
              <el-icon size="32"><Check /></el-icon>
              <p>暂无报警</p>
            </div>
          </div>
        </el-card>

        <!-- 系统状态 -->
        <el-card class="status-card">
          <template #header>
            <span>系统状态</span>
          </template>
          
          <div class="status-info">
            <div class="status-item">
              <span class="status-label">运行时长:</span>
              <span class="status-value">{{ monitoringDuration }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">检测总数:</span>
              <span class="status-value">{{ totalDetections }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">报警次数:</span>
              <span class="status-value">{{ realtimeAlerts.length }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="监控设置"
      width="600px"
    >
      <el-form :model="settings" label-width="120px">
        <el-form-item label="检测置信度">
          <el-slider
            v-model="settings.confidence"
            :min="0.1"
            :max="1.0"
            :step="0.05"
            show-stops
            show-input
          />
        </el-form-item>
        
        <el-form-item label="报警行为">
          <el-checkbox-group v-model="settings.alertBehaviors">
            <el-checkbox label="fall down">跌倒</el-checkbox>
            <el-checkbox label="fight">打斗</el-checkbox>
            <el-checkbox label="enter">闯入</el-checkbox>
            <el-checkbox label="exit">离开</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  VideoCamera, VideoPause, Setting, Warning, User, Search, Check 
} from '@element-plus/icons-vue'
import io from 'socket.io-client'
import { apiRequest } from '@/utils/api'

export default {
  name: 'RealtimeMonitor',
  components: {
    VideoCamera, VideoPause, Setting, Warning, User, Search, Check
  },
  setup() {
    const videoCanvas = ref(null)
    const isMonitoring = ref(false)
    const showSettings = ref(false)
    const currentFPS = ref(0)
    const processingTime = ref(0)
    const currentDetections = ref([])
    const realtimeAlerts = ref([])
    const monitoringDuration = ref('00:00:00')
    const totalDetections = ref(0)

    // 视频流URL
    const videoStreamUrl = ref('')
    
    const monitorConfig = reactive({
      source: 'camera',
      mode: 'realtime',
      recording: false,
      alertEnabled: true
    })
    
    const settings = reactive({
      confidence: 0.5,
      alertBehaviors: ['fall down', 'fight', 'enter', 'exit']
    })
    
    let websocket = null
    let monitoringStartTime = null
    let durationTimer = null
    let currentTaskId = null

    const startMonitoring = async () => {
      const source = monitorConfig.source === 'camera' ? 0 : monitorConfig.source;

      isMonitoring.value = true
      videoStreamUrl.value = `/video_feed?source=${source}&confidence=${settings.confidence}&_t=${new Date().getTime()}`
      monitoringStartTime = new Date()
      ElMessage.success('监控已启动')

      startDurationTimer()
    }

    const stopMonitoring = async () => {
      try {
        // 调用后端停止监控API
        const response = await fetch('/api/stop_monitoring', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result = await response.json()

        if (result.success) {
          // 更新前端状态
          isMonitoring.value = false
          currentDetections.value = []
          videoStreamUrl.value = ''
          ElMessage.success('监控已停止')

          // 清理WebSocket连接
          if (websocket) {
            websocket.close()
            websocket = null
          }

          // 清理定时器
          if (durationTimer) {
            clearInterval(durationTimer)
            durationTimer = null
          }
        } else {
          throw new Error(result.error || '停止监控失败')
        }
      } catch (error) {
        console.error('停止监控失败:', error)
        ElMessage.error(`停止监控失败: ${error.message}`)

        // 即使后端调用失败，也要清理前端状态
        isMonitoring.value = false
        currentDetections.value = []
        videoStreamUrl.value = ''

        if (websocket) {
          websocket.close()
          websocket = null
        }
        if (durationTimer) {
          clearInterval(durationTimer)
          durationTimer = null
        }
      }
    }

    const connectWebSocket = () => {
      const wsUrl = `ws://localhost:5001/detection`
      const socket = io(wsUrl, {
        transports: ['websocket'],
        path: '/socket.io/'
      });

      socket.on('connect', () => {
        console.log('WebSocket连接成功');
        socket.emit('join_task', { task_id: currentTaskId });
      });

      socket.on('realtime_result', (data) => {
        handleWebSocketMessage(data)
      });
      
      socket.on('disconnect', () => {
        console.log('WebSocket断开连接');
      });

      socket.on('connect_error', (error) => {
        console.error('WebSocket连接错误:', error);
      });

      websocket = socket;
    }

    const handleWebSocketMessage = (data) => {
      if (data.image) {
        const canvas = videoCanvas.value
        if (canvas) {
          const ctx = canvas.getContext('2d')
          const img = new Image()
          img.src = `data:image/jpeg;base64,${data.image}`
          img.onload = () => {
            if (!canvas.width || !canvas.height) {
              canvas.width = img.width;
              canvas.height = img.height;
            }
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
          }
        }
      }

      currentDetections.value = data.detections || []
      currentFPS.value = data.fps || 0
      processingTime.value = data.processingTime || 0
      totalDetections.value += data.detections?.length || 0

      if (data.type === 'alert') {
        handleAlert(data.alert)
      }
    }

    const handleAlert = (alert) => {
      realtimeAlerts.value.unshift({
        ...alert,
        id: Date.now(),
        timestamp: new Date(),
        level: 'high'
      })
      
      if (realtimeAlerts.value.length > 50) {
        realtimeAlerts.value = realtimeAlerts.value.slice(0, 50)
      }
    }

    const startDurationTimer = () => {
      durationTimer = setInterval(() => {
        const now = new Date()
        const diff = now - monitoringStartTime
        const hours = Math.floor(diff / 3600000)
        const minutes = Math.floor((diff % 3600000) / 60000)
        const seconds = Math.floor((diff % 60000) / 1000)
        
        monitoringDuration.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
      }, 1000)
    }

    const handleCanvasClick = () => {
    }

    const saveSettings = () => {
      localStorage.setItem('realtimeMonitorSettings', JSON.stringify(settings))
      ElMessage.success('设置已保存')
      showSettings.value = false
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString()
    }

    // 处理视频流错误
    const handleStreamError = (event) => {
      console.error('视频流加载错误:', event)
      ElMessage.error('视频流连接失败，请检查网络连接或切换到Canvas模式')
    }

    onUnmounted(() => {
      if (websocket) {
        websocket.close()
      }
      if (durationTimer) {
        clearInterval(durationTimer)
      }
    })

    return {
      videoCanvas,
      isMonitoring,
      showSettings,
      currentFPS,
      processingTime,
      currentDetections,
      realtimeAlerts,
      monitoringDuration,
      totalDetections,
      monitorConfig,
      settings,
      videoStreamUrl,
      startMonitoring,
      stopMonitoring,
      handleCanvasClick,
      handleStreamError,
      saveSettings,
      formatTime
    }
  }
}
</script>

<style scoped>
.realtime-monitor {
  padding: 0;
}

.control-panel {
  margin-bottom: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-buttons {
  display: flex;
  gap: 12px;
}

.control-row {
  margin-top: 16px;
}

.monitor-main {
  margin-bottom: 20px;
}

.video-card {
  height: 600px;
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fps-indicator {
  font-size: 12px;
  color: #67c23a;
  font-weight: bold;
}

.video-container {
  height: 520px;
  position: relative;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
}

.video-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.video-placeholder p {
  margin: 16px 0 0 0;
  font-size: 16px;
}

.video-display {
  height: 100%;
  position: relative;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.detection-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
}

.detection-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.detection-card,
.alert-card,
.status-card {
  margin-bottom: 16px;
  height: 180px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detection-list,
.alert-list {
  height: 120px;
  overflow-y: auto;
}

.detection-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 8px;
  background: #f5f7fa;
}

.detection-item.alert {
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
}

.detection-content {
  flex: 1;
  font-size: 12px;
}

.detection-behavior {
  font-weight: bold;
  color: #303133;
  margin-bottom: 2px;
}

.detection-confidence {
  color: #909399;
}

.alert-item {
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 12px;
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
}

.alert-time {
  color: #909399;
  margin-bottom: 2px;
}

.alert-behavior {
  font-weight: bold;
  color: #303133;
  margin-bottom: 2px;
}

.no-detections,
.no-alerts {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.no-detections p,
.no-alerts p {
  margin: 8px 0 0 0;
  font-size: 12px;
}

.status-info {
  padding: 8px 0;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-label {
  font-size: 12px;
  color: #606266;
}

.status-value {
  font-size: 12px;
  color: #303133;
  font-weight: bold;
}
</style> 