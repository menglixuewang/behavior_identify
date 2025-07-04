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
            <!-- 🔧 优先显示当前检测结果 -->
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

            <!-- 🔧 新增：显示行为统计摘要 -->
            <div v-if="currentDetections.length === 0 && realtimeStats.behavior_stats.length > 0" class="behavior-summary">
              <div class="summary-title">行为统计</div>
              <div
                v-for="behavior in realtimeStats.behavior_stats.slice(0, 3)"
                :key="behavior.behavior_type"
                class="behavior-stat-item"
              >
                <span class="behavior-name">{{ behavior.behavior_name }}</span>
                <span class="behavior-count">{{ behavior.count }}</span>
              </div>
            </div>

            <div v-if="currentDetections.length === 0 && realtimeStats.behavior_stats.length === 0" class="no-detections">
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
              <el-badge :value="realtimeStats.total_alerts" :max="99" />
            </div>
          </template>

          <div class="alert-list">
            <!-- 🔧 优先显示统计数据中的最近报警 -->
            <div
              v-for="alert in realtimeStats.recent_alerts"
              :key="`stats-${alert.time}-${alert.object_id}`"
              class="alert-item high"
            >
              <div class="alert-time">{{ alert.time }}</div>
              <div class="alert-behavior">{{ alert.behavior_name }}</div>
              <div class="alert-confidence">{{ (alert.confidence * 100).toFixed(1) }}%</div>
            </div>

            <!-- 🔧 兼容：如果统计数据中没有报警，显示传统报警列表 -->
            <div
              v-if="realtimeStats.recent_alerts.length === 0"
              v-for="alert in realtimeAlerts.slice(0, 5)"
              :key="alert.id"
              class="alert-item"
              :class="alert.level"
            >
              <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
              <div class="alert-behavior">{{ alert.behavior }}</div>
              <div class="alert-confidence">{{ (alert.confidence * 100).toFixed(1) }}%</div>
            </div>

            <div v-if="realtimeStats.recent_alerts.length === 0 && realtimeAlerts.length === 0" class="no-alerts">
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
              <span class="status-value">{{ realtimeStats.runtime_text || monitoringDuration }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">检测总数:</span>
              <span class="status-value">{{ realtimeStats.total_detections || totalDetections }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">报警次数:</span>
              <span class="status-value">{{ realtimeStats.total_alerts || realtimeAlerts.length }}</span>
            </div>
            <!-- 🔧 新增：显示平均FPS -->
            <div class="status-item" v-if="realtimeStats.avg_fps > 0">
              <span class="status-label">平均FPS:</span>
              <span class="status-value">{{ realtimeStats.avg_fps }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="监控设置"
      width="800px"
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
            :input-size="'small'"
          />
        </el-form-item>

        <el-form-item label="设备类型">
          <el-radio-group v-model="settings.device">
            <el-radio
              v-for="option in deviceOptions"
              :key="option.label"
              :label="option.label"
            >
              {{ option.name }}
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="报警行为">
          <el-checkbox-group v-model="settings.alertBehaviors" class="alert-behaviors-grid">
            <!-- 第一行：前4个行为 -->
            <div class="behavior-row">
              <el-checkbox
                v-for="behavior in availableBehaviors.slice(0, 4)"
                :key="behavior.label"
                :label="behavior.label"
                class="behavior-item"
              >
                {{ behavior.name }}
              </el-checkbox>
            </div>
            <!-- 第二行：后4个行为 -->
            <div class="behavior-row">
              <el-checkbox
                v-for="behavior in availableBehaviors.slice(4, 8)"
                :key="behavior.label"
                :label="behavior.label"
                class="behavior-item"
              >
                {{ behavior.name }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="cancelSettings">取消</el-button>
        <el-button @click="resetSettings">重置</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  VideoCamera, VideoPause, Setting, Warning, User, Search, Check
} from '@element-plus/icons-vue'
import io from 'socket.io-client'
import {
  configManager,
  AVAILABLE_BEHAVIORS,
  DEVICE_OPTIONS
} from '@/utils/configManager'

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

    // 停止监控状态标志，用于忽略主动断开连接时的错误
    const isStopping = ref(false)
    
    const monitorConfig = reactive({
      source: 'camera',
      mode: 'realtime',
      recording: false,
      alertEnabled: true
    })
    
    // 🔧 使用统一配置管理
    const settings = reactive(configManager.getConfig('realtime'))

    // 调试信息
    console.log('📺 [实时监控] 页面初始配置:', settings)
    console.log('📺 [实时监控] 初始报警行为:', settings.alertBehaviors)

    // 配置选项
    const availableBehaviors = AVAILABLE_BEHAVIORS
    const deviceOptions = DEVICE_OPTIONS

    console.log('📺 [实时监控] 可用报警行为:', availableBehaviors)

    // 监听报警行为配置变化
    watch(() => settings.alertBehaviors, (newBehaviors, oldBehaviors) => {
      console.log('🚨 [实时监控] 报警行为配置变化:')
      console.log('  旧值:', oldBehaviors)
      console.log('  新值:', newBehaviors)
      console.log('  选中数量:', newBehaviors?.length || 0)
      // 自动保存配置
      configManager.saveConfig(settings, 'realtime')
    }, { deep: true })

    // 监听其他配置变化
    watch(() => settings.confidence, (newVal, oldVal) => {
      console.log('🎯 [实时监控] 置信度变化:', oldVal, '->', newVal)
      configManager.saveConfig(settings, 'realtime')
    })

    watch(() => settings.device, (newVal, oldVal) => {
      console.log('💻 [实时监控] 设备变化:', oldVal, '->', newVal)
      configManager.saveConfig(settings, 'realtime')
    })
    
    let websocket = null
    let monitoringStartTime = null
    let durationTimer = null
    let currentTaskId = null

    const startMonitoring = async () => {
      const source = monitorConfig.source === 'camera' ? 0 : monitorConfig.source;

      isMonitoring.value = true

      // 🔧 使用统一配置管理，构建完整配置
      const config = configManager.toBackendFormat(settings, 'realtime')

      // 构建URL参数
      const params = new URLSearchParams()
      params.append('source', source)
      params.append('config', JSON.stringify(config))
      params.append('_t', new Date().getTime().toString())

      if (monitorConfig.mode === 'preview') {
        params.append('preview_only', 'true')
      }

      videoStreamUrl.value = `/video_feed?${params.toString()}`

      monitoringStartTime = new Date()

      // 🔧 修复：在非预览模式下连接WebSocket获取统计数据
      if (monitorConfig.mode !== 'preview') {
        // 延迟连接WebSocket，避免影响基本功能
        setTimeout(() => {
          try {
            connectWebSocket()
          } catch (error) {
            console.warn('WebSocket连接失败，但不影响基本监控功能:', error)
          }
        }, 1000)
      }

      // 根据模式显示不同的成功消息
      if (monitorConfig.mode === 'preview') {
        ElMessage.success('预览模式已启动')
      } else {
        ElMessage.success('实时检测已启动')
      }

      startDurationTimer()
    }

    const stopMonitoring = async () => {
      try {
        console.log('🛑 前端：开始停止监控流程')

        // 设置停止状态标志，用于忽略主动断开连接的错误
        isStopping.value = true

        // 🔧 关键修复：先断开视频流连接，再调用停止API
        // 1. 立即断开视频流连接，模拟页面关闭的效果
        console.log('🛑 前端：断开视频流连接')
        videoStreamUrl.value = ''  // 清空视频流URL，断开img标签的连接

        // 2. 等待一小段时间，确保连接断开
        await new Promise(resolve => setTimeout(resolve, 100))

        // 3. 调用后端停止监控API
        console.log('🛑 前端：调用停止监控API')
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
        console.log('🛑 前端：收到API响应', result)

        if (result.success) {
          // 更新前端状态
          isMonitoring.value = false
          currentDetections.value = []
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

          console.log('🛑 前端：停止监控完成')
        } else {
          throw new Error(result.error || '停止监控失败')
        }
      } catch (error) {
        console.error('🛑 前端：停止监控失败:', error)
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
      } finally {
        // 重置停止状态标志
        isStopping.value = false
      }
    }

    const connectWebSocket = () => {
      if (websocket) {
        websocket.close()
        websocket = null
      }

      // 🔧 修复：直接连接到/detection命名空间，增加超时和重连设置
      const wsUrl = `http://localhost:5001/detection`
      const detectionSocket = io(wsUrl, {
        transports: ['websocket', 'polling'],
        path: '/socket.io/',
        timeout: 10000,  // 10秒连接超时
        reconnection: true,  // 启用自动重连
        reconnectionAttempts: 3,  // 最多重连3次
        reconnectionDelay: 2000,  // 重连延迟2秒
        forceNew: true  // 强制创建新连接
      });

      detectionSocket.on('connect', () => {
        console.log('WebSocket连接成功');
        if (currentTaskId) {
          detectionSocket.emit('join_task', { task_id: currentTaskId });
        }
      });

      detectionSocket.on('realtime_result', (data) => {
        console.log('收到实时检测结果:', data)
        handleWebSocketMessage(data)
      });

      detectionSocket.on('progress_update', (data) => {
        console.log('收到进度更新:', data)
        // 处理进度更新
      });

      detectionSocket.on('task_completed', (data) => {
        console.log('任务完成:', data)
        // 处理任务完成
      });

      detectionSocket.on('disconnect', (reason) => {
        console.log('WebSocket断开连接:', reason);
      });

      detectionSocket.on('connect_error', (error) => {
        console.error('WebSocket连接错误:', error);
        // 如果是超时错误，尝试降级到polling模式
        if (error.message && error.message.includes('timeout')) {
          console.log('尝试使用polling模式重连...');
          setTimeout(() => {
            connectWebSocketWithPolling();
          }, 3000);
        }
      });

      detectionSocket.on('reconnect_failed', () => {
        console.warn('WebSocket重连失败，但不影响基本监控功能');
      });

      websocket = detectionSocket;
    }

    // 🔧 新增：使用polling模式的WebSocket连接（备用方案）
    const connectWebSocketWithPolling = () => {
      if (websocket) {
        websocket.close()
        websocket = null
      }

      const wsUrl = `http://localhost:5001/detection`
      const detectionSocket = io(wsUrl, {
        transports: ['polling'],  // 只使用polling模式
        path: '/socket.io/',
        timeout: 15000,  // 15秒超时
        reconnection: false  // 不自动重连
      });

      detectionSocket.on('connect', () => {
        console.log('WebSocket(polling模式)连接成功');
      });

      detectionSocket.on('realtime_result', (data) => {
        console.log('收到实时检测结果(polling):', data)
        handleWebSocketMessage(data)
      });

      detectionSocket.on('connect_error', (error) => {
        console.warn('WebSocket(polling模式)连接失败，但不影响基本监控功能:', error);
      });

      websocket = detectionSocket;
    }

    // 🔧 新增：实时统计数据
    const realtimeStats = reactive({
      runtime_text: '00:00:00',
      total_detections: 0,
      total_alerts: 0,
      avg_fps: 0,
      behavior_stats: [],
      recent_alerts: []
    })

    const handleWebSocketMessage = (data) => {
      console.log('收到WebSocket消息:', data)

      // 处理Canvas图像数据（如果有）
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

      // 🔧 修复：处理不同类型的WebSocket消息
      if (data.type === 'detection_result') {
        // 更新检测结果
        currentDetections.value = data.detections || []
        currentFPS.value = data.fps || 0
        processingTime.value = data.processing_time || 0

        // 累计检测总数
        if (data.detections && data.detections.length > 0) {
          totalDetections.value += data.detections.length
        }

      } else if (data.type === 'alert') {
        // 处理报警消息
        handleAlert({
          type: data.alert_type,
          detection: data.detection,
          timestamp: data.detection?.timestamp || Date.now()
        })

      } else if (data.type === 'statistics_update') {
        // 🔧 新增：处理统计数据更新
        handleStatisticsUpdate(data.statistics)

      } else {
        // 兼容旧格式的消息
        currentDetections.value = data.detections || []
        currentFPS.value = data.fps || 0
        processingTime.value = data.processingTime || data.processing_time || 0

        if (data.detections && data.detections.length > 0) {
          totalDetections.value += data.detections.length
        }

        if (data.type === 'alert') {
          handleAlert(data.alert)
        }
      }
    }

    // 🔧 新增：处理统计数据更新
    const handleStatisticsUpdate = (statistics) => {
      if (!statistics) return

      // 更新统计数据
      Object.assign(realtimeStats, {
        runtime_text: statistics.runtime_text || '00:00:00',
        total_detections: statistics.total_detections || 0,
        total_alerts: statistics.total_alerts || 0,
        avg_fps: statistics.avg_fps || 0,
        behavior_stats: statistics.behavior_stats || [],
        recent_alerts: statistics.recent_alerts || []
      })

      // 同步更新现有的显示数据
      monitoringDuration.value = statistics.runtime_text || '00:00:00'
      totalDetections.value = statistics.total_detections || 0
      currentFPS.value = statistics.avg_fps || currentFPS.value

      console.log('统计数据已更新:', realtimeStats)
    }

    const handleAlert = (alert) => {
      // 🔧 修复：创建标准化的报警对象
      const alertObj = {
        id: Date.now(),
        type: alert.type || alert.alert_type || 'unknown',
        timestamp: new Date(alert.timestamp || Date.now()),
        level: 'high',
        confidence: alert.detection?.confidence || 0,
        description: `检测到异常行为: ${alert.type || alert.alert_type}`,
        frame_number: alert.detection?.frame_number,
        object_id: alert.detection?.object_id,
        behavior_type: alert.detection?.behavior_type
      }

      realtimeAlerts.value.unshift(alertObj)

      // 限制报警列表长度
      if (realtimeAlerts.value.length > 50) {
        realtimeAlerts.value = realtimeAlerts.value.slice(0, 50)
      }

      // 🔧 新增：显示报警通知
      ElNotification({
        title: '异常行为报警',
        message: alertObj.description,
        type: 'warning',
        duration: 5000
      })

      // 播放报警声音（如果启用）
      if (monitorConfig.alertEnabled) {
        playAlertSound()
      }
    }

    // 🔧 新增：播放报警声音
    const playAlertSound = () => {
      try {
        // 创建简单的报警音效
        const audioContext = new (window.AudioContext || window.webkitAudioContext)()
        const oscillator = audioContext.createOscillator()
        const gainNode = audioContext.createGain()

        oscillator.connect(gainNode)
        gainNode.connect(audioContext.destination)

        oscillator.frequency.setValueAtTime(800, audioContext.currentTime)
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)

        oscillator.start(audioContext.currentTime)
        oscillator.stop(audioContext.currentTime + 0.5)
      } catch (error) {
        console.warn('无法播放报警声音:', error)
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
      // 验证配置
      const validation = configManager.validateConfig(settings)
      if (!validation.isValid) {
        ElMessage.error('配置验证失败: ' + validation.errors.join(', '))
        return
      }

      // 保存配置
      configManager.saveConfig(settings, 'realtime')
      ElMessage.success('设置已保存')
      showSettings.value = false
    }

    const cancelSettings = () => {
      // 重新加载配置，取消更改
      Object.assign(settings, configManager.getConfig('realtime'))
      showSettings.value = false
    }

    const resetSettings = () => {
      // 重置为默认配置
      configManager.resetConfig()
      Object.assign(settings, configManager.getConfig('realtime'))
      ElMessage.success('配置已重置为默认值')
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString()
    }

    // 处理视频流错误
    const handleStreamError = (event) => {
      console.error('视频流加载错误:', event)

      // 如果正在停止监控，忽略错误消息（这是主动断开连接导致的）
      if (isStopping.value) {
        console.log('🛑 前端：忽略停止监控时的连接错误')
        return
      }

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
      isStopping,
      realtimeStats, // 🔧 新增：实时统计数据
      // 配置选项
      availableBehaviors,
      deviceOptions,
      // 方法
      startMonitoring,
      stopMonitoring,
      handleCanvasClick,
      handleStreamError,
      saveSettings,
      cancelSettings,
      resetSettings,
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

/* 🔧 新增：行为统计摘要样式 */
.behavior-summary {
  padding: 12px;
  background: #f0f9ff;
  border-radius: 6px;
  border: 1px solid #e1f5fe;
}

.summary-title {
  font-size: 13px;
  font-weight: bold;
  color: #1976d2;
  margin-bottom: 8px;
}

.behavior-stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
}

.behavior-name {
  color: #303133;
}

.behavior-count {
  color: #1976d2;
  font-weight: bold;
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

/* 报警行为自适应布局 */
.alert-behaviors-grid {
  width: 100%;
}

.behavior-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  width: 100%;
}

.behavior-row:last-child {
  margin-bottom: 0;
}

.behavior-item {
  flex: 1;
  display: flex;
  justify-content: center;
  margin: 0 4px;
}

.behavior-item:first-child {
  margin-left: 0;
}

.behavior-item:last-child {
  margin-right: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  /* 小屏幕下报警行为布局调整 */
  .behavior-row {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .behavior-item {
    flex: 0 0 calc(50% - 8px);
    margin: 4px;
    justify-content: flex-start;
  }
}
</style>