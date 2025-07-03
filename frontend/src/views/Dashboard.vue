<template>
  <div class="dashboard">
    <!-- 系统状态卡片 -->
    <el-row :gutter="20" class="status-cards">
      <el-col :span="6">
        <el-card class="status-card">
          <div class="card-content">
            <div class="card-icon online">
              <el-icon size="32"><VideoCamera /></el-icon>
            </div>
            <div class="card-info">
              <h3>{{ stats.activeTasks }}</h3>
              <p>活跃任务</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="status-card">
          <div class="card-content">
            <div class="card-icon warning">
              <el-icon size="32"><Warning /></el-icon>
            </div>
            <div class="card-info">
              <h3>{{ stats.todayAlerts }}</h3>
              <p>今日报警</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="status-card">
          <div class="card-content">
            <div class="card-icon success">
              <el-icon size="32"><DataAnalysis /></el-icon>
            </div>
            <div class="card-info">
              <h3>{{ stats.totalDetections }}</h3>
              <p>检测总数</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="status-card">
          <div class="card-content">
            <div class="card-icon info">
              <el-icon size="32"><Clock /></el-icon>
            </div>
            <div class="card-info">
              <h3>{{ systemUptime }}</h3>
              <p>系统运行时间</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主要内容区域 -->
    <el-row :gutter="20" class="main-content">
      <!-- 实时监控预览 -->
      <el-col :span="16">
        <el-card class="preview-card">
          <template #header>
            <div class="card-header">
              <span>实时监控预览</span>
              <div class="header-buttons">
                <el-button
                  v-if="isMonitoring"
                  type="danger"
                  size="small"
                  @click="stopMonitoring"
                >
                  <el-icon><VideoPause /></el-icon>
                  停止监控
                </el-button>
                <el-button type="primary" size="small" @click="$router.push('/realtime')">
                  查看详情
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="monitor-preview">
            <div v-if="!isMonitoring" class="no-monitor">
              <el-icon size="64"><VideoCamera /></el-icon>
              <p>暂无实时监控</p>
              <el-button type="primary" @click="startMonitoring">开始监控</el-button>
            </div>
            
            <div v-else class="monitor-active">
              <img
                :src="videoStreamUrl"
                class="video-preview"
                alt="实时监控视频流"
                @error="handleStreamError"
              />
              <div class="monitor-overlay">
                <div class="monitor-info">
                  <span class="status-indicator online"></span>
                  <span>监控中 - {{ currentFPS }} FPS</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 最近报警 -->
      <el-col :span="8">
        <el-card class="alerts-card">
          <template #header>
            <div class="card-header">
              <span>最近报警</span>
              <el-button type="text" size="small" @click="$router.push('/alerts')">
                查看全部
              </el-button>
            </div>
          </template>
          
          <div class="alerts-list">
            <div 
              v-for="alert in recentAlerts" 
              :key="alert.id"
              class="alert-item"
              :class="alert.level"
            >
              <div class="alert-icon">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="alert-content">
                <div class="alert-title">{{ alert.behavior }}</div>
                <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
                <div class="alert-location">{{ alert.location }}</div>
              </div>
            </div>
            
            <div v-if="recentAlerts.length === 0" class="no-alerts">
              <el-icon size="32"><Check /></el-icon>
              <p>暂无报警记录</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计图表 -->
    <el-row :gutter="20" class="charts-section">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>检测行为分布</span>
          </template>
          <div id="behaviorChart" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>24小时检测趋势</span>
          </template>
          <div id="trendChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, VideoPause, Warning, DataAnalysis, Clock, Check } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { apiRequest, API_BASE_URL } from '@/utils/api'
import io from 'socket.io-client'

export default {
  name: 'Dashboard',
  components: {
    VideoCamera, VideoPause, Warning, DataAnalysis, Clock, Check
  },
  setup() {
    const stats = reactive({
      activeTasks: 0,
      todayAlerts: 0,
      totalDetections: 0
    })
    
    const systemUptime = ref('0天0小时')
    const isMonitoring = ref(false)
    const currentFPS = ref(0)
    const recentAlerts = ref([])
    const videoPreview = ref(null)
    const videoStreamUrl = ref('')
    
    let updateTimer = null
    let websocket = null
    let behaviorChart = null
    let trendChart = null
    let currentTaskId = null

    // 获取系统统计信息
    const fetchStats = async () => {
      try {
        const response = await apiRequest('/api/statistics/overview')
        if (response.success) {
          stats.activeTasks = response.activeTasks || 0
          stats.todayAlerts = response.todayAlerts || 0
          stats.totalDetections = response.totalDetections || 0
        }
      } catch (error) {
        console.error('获取统计信息失败:', error)
      }
    }

    // 获取系统运行时间
    const fetchUptime = async () => {
      try {
        const response = await apiRequest('/api/system/uptime')
        if (response.success) {
          systemUptime.value = response.uptime || '0天0小时'
        }
      } catch (error) {
        console.error('获取系统运行时间失败:', error)
      }
    }

    // 获取最近报警
    const fetchRecentAlerts = async () => {
      try {
        const response = await apiRequest('/api/alerts?per_page=5')
        if (response.success && response.alerts) {
          recentAlerts.value = response.alerts.slice(0, 5).map(alert => ({
            id: alert.id,
            behavior: alert.trigger_behavior || alert.alert_type,
            timestamp: alert.created_at,
            location: `任务 ${alert.task_id}`,
            level: getLevelByBehavior(alert.alert_type)
          }))
        }
      } catch (error) {
        console.error('获取最近报警失败:', error)
      }
    }

    // 获取图表数据
    const fetchChartsData = async () => {
      try {
        const response = await apiRequest('/api/statistics/charts?period=24h')
        if (response.success && response.charts) {
          updateBehaviorChart(response.charts.behaviorDistribution || [])
          updateTrendChart(response.charts.trendAnalysis || [])
        }
      } catch (error) {
        console.error('获取图表数据失败:', error)
        // 如果API失败，使用空数据初始化图表
        updateBehaviorChart([])
        updateTrendChart([])
      }
    }

    // 根据行为类型获取报警级别
    const getLevelByBehavior = (behavior) => {
      const highRisk = ['fall down', 'fight', 'enter']
      const mediumRisk = ['run', 'exit']
      
      if (highRisk.includes(behavior)) return 'high'
      if (mediumRisk.includes(behavior)) return 'medium'
      return 'low'
    }

    // 更新行为分布饼图
    const updateBehaviorChart = (data) => {
      if (!behaviorChart) return
      
      const option = {
        title: {
          text: data.length > 0 ? '检测行为分布' : '暂无数据',
          left: 'center',
          textStyle: {
            fontSize: 14,
            color: '#333'
          }
        },
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        legend: {
          orient: 'vertical',
          left: 'left',
          textStyle: {
            fontSize: 12
          }
        },
        series: [
          {
            name: '检测次数',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['60%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: {
              show: false,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 16,
                fontWeight: 'bold'
              }
            },
            labelLine: {
              show: false
            },
            data: data.length > 0 ? data.map(item => ({
              value: item.value,
              name: item.name,
              itemStyle: {
                color: getColorByBehavior(item.behavior_type)
              }
            })) : [{
              value: 1,
              name: '暂无数据',
              itemStyle: { color: '#e5e5e5' },
              label: { show: true, formatter: '暂无数据' }
            }]
          }
        ]
      }
      
      behaviorChart.setOption(option)
    }

    // 更新趋势折线图
    const updateTrendChart = (data) => {
      if (!trendChart) return
      
      const option = {
        title: {
          text: '24小时检测趋势',
          left: 'center',
          textStyle: {
            fontSize: 14,
            color: '#333'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross',
            label: {
              backgroundColor: '#6a7985'
            }
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: [
          {
            type: 'category',
            boundaryGap: false,
            data: data.length > 0 ? data.map(item => item.time) : Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`)
          }
        ],
        yAxis: [
          {
            type: 'value',
            name: '检测次数',
            min: 0,
            minInterval: 1,
            max: (value) => (value.max > 4 ? value.max : 5)
          }
        ],
        series: [
          {
            name: '检测次数',
            type: 'line',
            stack: 'Total',
            smooth: true,
            lineStyle: {
              width: 3
            },
            areaStyle: {
              opacity: 0.3,
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                {
                  offset: 0,
                  color: 'rgba(58, 77, 233, 0.8)'
                },
                {
                  offset: 1,
                  color: 'rgba(58, 77, 233, 0.1)'
                }
              ])
            },
            emphasis: {
              focus: 'series'
            },
            data: data.length > 0 ? data.map(item => item.value) : Array(24).fill(0)
          }
        ]
      }
      
      trendChart.setOption(option)
    }

    // 根据行为类型获取颜色
    const getColorByBehavior = (behavior) => {
      const colorMap = {
        'fall down': '#ff4757',  // 红色 - 跌倒
        'fight': '#ff6b7a',      // 粉红 - 打斗
        'enter': '#1e90ff',      // 蓝色 - 闯入
        'exit': '#54a0ff',       // 浅蓝 - 离开
        'run': '#ffa502',        // 橙色 - 奔跑
        'sit': '#2ed573',        // 绿色 - 坐下
        'stand': '#7bed9f',      // 浅绿 - 站立
        'walk': '#70a1ff'        // 紫色 - 行走
      }
      return colorMap[behavior] || '#a4b0be'
    }

    // 开始监控
    const startMonitoring = async () => {
      try {
        // 使用我们统一的apiRequest，它会自动处理body的序列化
        const response = await apiRequest('/api/detect/realtime', {
          method: 'POST',
          body: {
            source: 0,
            confidence: 0.4, // 使用一个合理的默认值
            preview: true
          }
        })
        
        if (response.success) {
          isMonitoring.value = true
          currentTaskId = response.task_id
          // 设置视频流URL
          videoStreamUrl.value = `${API_BASE_URL}/video_feed?source=0&confidence=0.4&_t=${new Date().getTime()}`
          ElMessage.success('监控预览已启动')
          connectWebSocket()
        } else {
          ElMessage.error(response.error || '启动监控失败')
        }
      } catch (error) {
        ElMessage.error(`启动监控失败: ${error.message}`)
        console.error('启动监控错误:', error)
      }
    }

    // 停止监控
    const stopMonitoring = async () => {
      console.log('停止监控按钮被点击')
      try {
        console.log('发送停止监控请求...')
        const response = await apiRequest('/api/stop_monitoring', {
          method: 'POST'
        })

        console.log('停止监控响应:', response)
        if (response.success) {
          // 更新前端状态
          isMonitoring.value = false
          videoStreamUrl.value = ''
          currentFPS.value = 0
          currentTaskId = null
          ElMessage.success('监控已停止')

          // 清理WebSocket连接
          if (websocket) {
            websocket.close()
            websocket = null
          }
        } else {
          ElMessage.error(response.error || '停止监控失败')
        }
      } catch (error) {
        ElMessage.error(`停止监控失败: ${error.message}`)
        console.error('停止监控错误:', error)

        // 即使后端调用失败，也要清理前端状态
        isMonitoring.value = false
        videoStreamUrl.value = ''
        currentFPS.value = 0
        currentTaskId = null

        if (websocket) {
          websocket.close()
          websocket = null
        }
      }
    }

    // 处理视频流错误
    const handleStreamError = (event) => {
      console.error('视频流加载错误:', event)
      ElMessage.error('视频流连接失败，请检查网络连接')
    }

    // WebSocket连接
    const connectWebSocket = () => {
      // 确保URL正确指向后端的SocketIO服务
      const wsUrl = `ws://localhost:5001/detection`
      const socket = io(wsUrl, {
        transports: ['websocket'],
        path: '/socket.io/'
      });

      socket.on('connect', () => {
        console.log('Dashboard WebSocket 连接成功');
        if (currentTaskId) {
          socket.emit('join_task', { task_id: currentTaskId });
        }
      });
      
      socket.on('realtime_result', (data) => {
        // Dashboard 预览只关心FPS和报警信息
        if (data.fps) {
          currentFPS.value = data.fps;
        }
        if (data.type === 'alert') {
          // 收到新报警，可以触发相关数据刷新
          fetchRecentAlerts()
          // 也可以考虑只在前端列表加一个，减少API请求
        }
      });
      
      socket.on('disconnect', () => {
        console.log('Dashboard WebSocket 断开连接');
      });

      socket.on('connect_error', (error) => {
        console.error('Dashboard WebSocket 连接错误:', error);
      });

      websocket = socket;
    }

    // 格式化时间
    const formatTime = (timestamp) => {
      const date = new Date(timestamp)
      const now = new Date()
      const diff = now - date
      
      if (diff < 60000) {
        return '刚刚'
      } else if (diff < 3600000) {
        return `${Math.floor(diff / 60000)}分钟前`
      } else if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)}小时前`
      } else {
        return date.toLocaleDateString()
      }
    }

    // 视频加载完成
    const onVideoLoaded = () => {
      console.log('视频预览加载完成')
    }

    // 初始化图表
    const initCharts = async () => {
      await nextTick()
      
      // 初始化行为分布图
      const behaviorChartDom = document.getElementById('behaviorChart')
      if (behaviorChartDom) {
        behaviorChart = echarts.init(behaviorChartDom)
        
        // 窗口大小改变时重新调整图表
        window.addEventListener('resize', () => {
          behaviorChart?.resize()
        })
      }
      
      // 初始化趋势图
      const trendChartDom = document.getElementById('trendChart')
      if (trendChartDom) {
        trendChart = echarts.init(trendChartDom)
        
        // 窗口大小改变时重新调整图表
        window.addEventListener('resize', () => {
          trendChart?.resize()
        })
      }
      
      // 获取图表数据
      fetchChartsData()
    }

    onMounted(() => {
      fetchStats()
      fetchUptime()
      fetchRecentAlerts()
      initCharts()
      
      // 定期更新数据
      updateTimer = setInterval(() => {
        fetchStats()
        fetchUptime()
        fetchRecentAlerts()
        fetchChartsData()
      }, 30000) // 每30秒更新一次
    })

    onUnmounted(() => {
      if (updateTimer) {
        clearInterval(updateTimer)
      }
      if (websocket) {
        websocket.close()
      }
      
      // 销毁图表实例
      behaviorChart?.dispose()
      trendChart?.dispose()
      
      // 移除resize监听器
      window.removeEventListener('resize', () => {
        behaviorChart?.resize()
        trendChart?.resize()
      })
    })

    return {
      stats,
      systemUptime,
      isMonitoring,
      currentFPS,
      recentAlerts,
      videoPreview,
      videoStreamUrl,
      startMonitoring,
      stopMonitoring,
      handleStreamError,
      formatTime,
      onVideoLoaded
    }
  }
}
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.status-cards {
  margin-bottom: 20px;
}

.status-card {
  transition: transform 0.2s;
}

.status-card:hover {
  transform: translateY(-2px);
}

.card-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.card-icon.online {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.card-icon.warning {
  background: linear-gradient(135deg, #e6a23c, #f0a020);
}

.card-icon.success {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.card-icon.info {
  background: linear-gradient(135deg, #909399, #b1b5b8);
}

.card-info h3 {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.card-info p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.main-content {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.preview-card {
  height: 480px;
}

.monitor-preview {
  height: 400px;
  position: relative;
}

.no-monitor {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.no-monitor p {
  margin: 16px 0;
  font-size: 16px;
}

.monitor-active {
  height: 100%;
  position: relative;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
}

.video-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.monitor-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
  right: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.monitor-info {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.online {
  background: #67c23a;
  box-shadow: 0 0 6px #67c23a;
}

.alerts-card {
  height: 400px;
}

.alerts-list {
  height: 320px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  border-left: 3px solid;
  background: #fafafa;
}

.alert-item.high {
  border-left-color: #f56c6c;
  background: #fef0f0;
}

.alert-item.medium {
  border-left-color: #e6a23c;
  background: #fdf6ec;
}

.alert-item.low {
  border-left-color: #409eff;
  background: #ecf5ff;
}

.alert-icon {
  color: #f56c6c;
  margin-top: 2px;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.alert-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 2px;
}

.alert-location {
  font-size: 12px;
  color: #606266;
}

.no-alerts {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.no-alerts p {
  margin: 12px 0 0 0;
}

.charts-section {
  margin-bottom: 20px;
}

.chart-container {
  height: 350px;
  width: 100%;
}
</style> 