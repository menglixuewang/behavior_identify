<template>
  <div class="statistics">
    <!-- 时间范围选择 -->
    <el-card class="time-range-card">
      <div class="time-range-header">
        <span>统计时间范围</span>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          @change="handleTimeRangeChange"
        />
      </div>
    </el-card>

    <!-- 概览统计 -->
    <el-row :gutter="20" class="overview-stats">
      <el-col :span="6">
        <el-card class="overview-card">
          <div class="overview-content">
            <div class="overview-icon detections">
              <el-icon size="32"><DataAnalysis /></el-icon>
            </div>
            <div class="overview-info">
              <div class="overview-value">{{ overviewStats.totalDetections }}</div>
              <div class="overview-label">总检测数</div>
              <div class="overview-change" :class="{ 'positive': overviewStats.detectionsChange > 0 }">
                {{ overviewStats.detectionsChange > 0 ? '+' : '' }}{{ overviewStats.detectionsChange }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="overview-card">
          <div class="overview-content">
            <div class="overview-icon alerts">
              <el-icon size="32"><Warning /></el-icon>
            </div>
            <div class="overview-info">
              <div class="overview-value">{{ overviewStats.totalAlerts }}</div>
              <div class="overview-label">总报警数</div>
              <div class="overview-change" :class="{ 'positive': overviewStats.alertsChange > 0 }">
                {{ overviewStats.alertsChange > 0 ? '+' : '' }}{{ overviewStats.alertsChange }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="overview-card">
          <div class="overview-content">
            <div class="overview-icon tasks">
              <el-icon size="32"><List /></el-icon>
            </div>
            <div class="overview-info">
              <div class="overview-value">{{ overviewStats.totalTasks }}</div>
              <div class="overview-label">处理任务</div>
              <div class="overview-change" :class="{ 'positive': overviewStats.tasksChange > 0 }">
                {{ overviewStats.tasksChange > 0 ? '+' : '' }}{{ overviewStats.tasksChange }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="overview-card">
          <div class="overview-content">
            <div class="overview-icon accuracy">
              <el-icon size="32"><TrendCharts /></el-icon>
            </div>
            <div class="overview-info">
              <div class="overview-value">{{ overviewStats.avgAccuracy }}%</div>
              <div class="overview-label">平均准确率</div>
              <div class="overview-change" :class="{ 'positive': overviewStats.accuracyChange > 0 }">
                {{ overviewStats.accuracyChange > 0 ? '+' : '' }}{{ overviewStats.accuracyChange }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-section">
      <!-- 检测趋势图 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>检测趋势分析</span>
              <el-button-group>
                <el-button 
                  v-for="period in timePeriods" 
                  :key="period.value"
                  :type="currentPeriod === period.value ? 'primary' : ''"
                  size="small"
                  @click="currentPeriod = period.value"
                >
                  {{ period.label }}
                </el-button>
              </el-button-group>
            </div>
          </template>
          <div ref="trendChart" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 行为分布图 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>行为类型分布</span>
          </template>
          <div ref="behaviorChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-section">
      <!-- 报警级别分布 -->
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>报警级别分布</span>
          </template>
          <div ref="alertLevelChart" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 时段分析 -->
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <span>24小时时段分析</span>
          </template>
          <div ref="hourlyChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细统计表格 -->
    <el-card class="detail-stats-card">
      <template #header>
        <div class="card-header">
          <span>详细统计数据</span>
          <el-button type="primary" size="small" @click="exportData">
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="card">
        <!-- 行为统计 -->
        <el-tab-pane label="行为统计" name="behavior">
          <el-table :data="behaviorStats" style="width: 100%">
            <el-table-column prop="behavior" label="行为类型" width="150">
              <template #default="scope">
                <div class="behavior-cell">
                  <el-icon><User /></el-icon>
                  <span>{{ getBehaviorText(scope.row.behavior) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="检测次数" width="120" />
            <el-table-column prop="percentage" label="占比" width="100">
              <template #default="scope">
                {{ scope.row.percentage }}%
              </template>
            </el-table-column>
            <el-table-column prop="avgConfidence" label="平均置信度" width="120">
              <template #default="scope">
                <el-progress 
                  :percentage="Math.round(scope.row.avgConfidence * 100)" 
                  :stroke-width="6"
                  :show-text="false"
                />
                <span style="margin-left: 8px;">{{ Math.round(scope.row.avgConfidence * 100) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="alertCount" label="报警次数" width="100" />
            <el-table-column prop="alertRate" label="报警率" width="100">
              <template #default="scope">
                {{ scope.row.alertRate }}%
              </template>
            </el-table-column>
            <el-table-column prop="trend" label="趋势" width="100">
              <template #default="scope">
                <el-tag 
                  :type="scope.row.trend === 'up' ? 'danger' : scope.row.trend === 'down' ? 'success' : 'info'"
                  size="small"
                >
                  {{ getTrendText(scope.row.trend) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 时间统计 -->
        <el-tab-pane label="时间统计" name="time">
          <el-table :data="timeStats" style="width: 100%">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="detections" label="检测数" width="100" />
            <el-table-column prop="alerts" label="报警数" width="100" />
            <el-table-column prop="tasks" label="任务数" width="100" />
            <el-table-column prop="avgProcessTime" label="平均处理时间" width="120">
              <template #default="scope">
                {{ scope.row.avgProcessTime }}ms
              </template>
            </el-table-column>
            <el-table-column prop="accuracy" label="准确率" width="100">
              <template #default="scope">
                {{ scope.row.accuracy }}%
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 设备统计 -->
        <el-tab-pane label="设备统计" name="device">
          <el-table :data="deviceStats" style="width: 100%">
            <el-table-column prop="device" label="设备类型" width="120" />
            <el-table-column prop="usage" label="使用次数" width="100" />
            <el-table-column prop="avgProcessTime" label="平均处理时间" width="120">
              <template #default="scope">
                {{ scope.row.avgProcessTime }}ms
              </template>
            </el-table-column>
            <el-table-column prop="successRate" label="成功率" width="100">
              <template #default="scope">
                {{ scope.row.successRate }}%
              </template>
            </el-table-column>
            <el-table-column prop="performance" label="性能评分" width="120">
              <template #default="scope">
                <el-rate 
                  v-model="scope.row.performance" 
                  :max="5" 
                  disabled 
                  show-score 
                  text-color="#ff9900"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  DataAnalysis, Warning, List, TrendCharts, Download, User 
} from '@element-plus/icons-vue'

export default {
  name: 'Statistics',
  components: {
    DataAnalysis, Warning, List, TrendCharts, Download, User
  },
  setup() {
    const timeRange = ref([])
    const activeTab = ref('behavior')
    const currentPeriod = ref('7d')
    
    // 图表DOM引用
    const trendChart = ref(null)
    const behaviorChart = ref(null)
    const alertLevelChart = ref(null)
    const hourlyChart = ref(null)
    
    // 概览统计数据
    const overviewStats = reactive({
      totalDetections: 0,
      detectionsChange: 0,
      totalAlerts: 0,
      alertsChange: 0,
      totalTasks: 0,
      tasksChange: 0,
      avgAccuracy: 0,
      accuracyChange: 0
    })
    
    // 详细统计数据
    const behaviorStats = ref([])
    const timeStats = ref([])
    const deviceStats = ref([])
    
    // 时间周期选项
    const timePeriods = [
      { label: '7天', value: '7d' },
      { label: '30天', value: '30d' },
      { label: '90天', value: '90d' },
      { label: '1年', value: '1y' }
    ]

    // 获取统计数据
    const fetchStatistics = async () => {
      try {
        const params = new URLSearchParams()
        if (timeRange.value && timeRange.value.length === 2) {
          params.append('startTime', timeRange.value[0].toISOString())
          params.append('endTime', timeRange.value[1].toISOString())
        }
        params.append('period', currentPeriod.value)
        
        const response = await fetch(`/api/statistics?${params}`)
        if (response.ok) {
          const data = await response.json()
          
          // 更新概览统计
          Object.assign(overviewStats, data.overview || {})
          
          // 更新详细统计
          behaviorStats.value = data.behaviors || []
          timeStats.value = data.timeStats || []
          deviceStats.value = data.devices || []
          
          // 更新图表
          await nextTick()
          updateCharts(data)
        }
      } catch (error) {
        console.error('获取统计数据失败:', error)
        ElMessage.error('获取统计数据失败')
      }
    }

    // 更新图表
    const updateCharts = (data) => {
      // 这里可以集成ECharts或其他图表库
      // 暂时用占位符显示
      console.log('更新图表数据:', data)
    }

    // 时间范围变化处理
    const handleTimeRangeChange = () => {
      fetchStatistics()
    }

    // 导出数据
    const exportData = async () => {
      try {
        const params = new URLSearchParams()
        if (timeRange.value && timeRange.value.length === 2) {
          params.append('startTime', timeRange.value[0].toISOString())
          params.append('endTime', timeRange.value[1].toISOString())
        }
        
        const response = await fetch(`/api/statistics/export?${params}`)
        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = `statistics_${new Date().toISOString().split('T')[0]}.xlsx`
          link.click()
          window.URL.revokeObjectURL(url)
          
          ElMessage.success('数据导出成功')
        } else {
          ElMessage.error('数据导出失败')
        }
      } catch (error) {
        ElMessage.error('数据导出失败')
        console.error('导出错误:', error)
      }
    }

    // 工具函数
    const getBehaviorText = (behavior) => {
      const textMap = {
        'fall down': '跌倒',
        'fight': '打斗',
        'enter': '闯入',
        'exit': '离开',
        'run': '奔跑',
        'sit': '坐下',
        'stand': '站立',
        'walk': '行走'
      }
      return textMap[behavior] || behavior
    }

    const getTrendText = (trend) => {
      const textMap = {
        'up': '上升',
        'down': '下降',
        'stable': '稳定'
      }
      return textMap[trend] || '未知'
    }

    // 监听周期变化
    watch(currentPeriod, () => {
      fetchStatistics()
    })

    onMounted(() => {
      // 设置默认时间范围为最近7天
      const endTime = new Date()
      const startTime = new Date()
      startTime.setDate(startTime.getDate() - 7)
      timeRange.value = [startTime, endTime]
      
      fetchStatistics()
    })

    return {
      timeRange,
      activeTab,
      currentPeriod,
      trendChart,
      behaviorChart,
      alertLevelChart,
      hourlyChart,
      overviewStats,
      behaviorStats,
      timeStats,
      deviceStats,
      timePeriods,
      handleTimeRangeChange,
      exportData,
      getBehaviorText,
      getTrendText
    }
  }
}
</script>

<style scoped>
.statistics {
  padding: 0;
}

.time-range-card {
  margin-bottom: 20px;
}

.time-range-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.overview-stats {
  margin-bottom: 20px;
}

.overview-card {
  transition: transform 0.2s;
}

.overview-card:hover {
  transform: translateY(-2px);
}

.overview-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.overview-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.overview-icon.detections {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.overview-icon.alerts {
  background: linear-gradient(135deg, #f56c6c, #f78989);
}

.overview-icon.tasks {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.overview-icon.accuracy {
  background: linear-gradient(135deg, #e6a23c, #f0a020);
}

.overview-info {
  flex: 1;
}

.overview-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.overview-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 4px;
}

.overview-change {
  font-size: 12px;
  font-weight: bold;
  color: #f56c6c;
}

.overview-change.positive {
  color: #67c23a;
}

.charts-section {
  margin-bottom: 20px;
}

.chart-card {
  height: 400px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  border-radius: 4px;
  color: #909399;
  font-size: 14px;
}

.chart-container::before {
  content: "图表加载中...";
}

.detail-stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.behavior-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-tabs__content) {
  padding-top: 20px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-rate) {
  height: auto;
}
</style> 