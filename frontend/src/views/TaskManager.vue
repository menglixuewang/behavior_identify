<template>
  <div class="task-manager">
    <!-- 任务统计 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon total">
              <el-icon size="24"><List /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ taskStats.total }}</div>
              <div class="stat-label">总任务数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon running">
              <el-icon size="24"><Loading /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ taskStats.running }}</div>
              <div class="stat-label">运行中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon completed">
              <el-icon size="24"><Check /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ taskStats.completed }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon failed">
              <el-icon size="24"><Close /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ taskStats.failed }}</div>
              <div class="stat-label">失败</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-card class="task-list-card">
      <template #header>
        <div class="card-header">
          <span>任务列表</span>
          <div class="header-actions">
            <el-button-group>
              <el-button 
                v-for="filter in statusFilters" 
                :key="filter.value"
                :type="currentFilter === filter.value ? 'primary' : ''"
                size="small"
                @click="currentFilter = filter.value"
              >
                {{ filter.label }}
              </el-button>
            </el-button-group>
            <el-button type="primary" size="small" @click="refreshTasks">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-section">
        <el-row :gutter="20">
          <el-col :span="7">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索任务名称或文件名"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          
          <el-col :span="4">
            <el-select v-model="typeFilter" placeholder="任务类型" clearable style="width: 100%">
              <el-option label="视频检测" value="video" />
              <el-option label="实时监控" value="realtime" />
            </el-select>
          </el-col>
          
          <el-col :span="7">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              size="default"
              style="width: 100%"
              @change="handleDateChange"
            />
          </el-col>
          
          <el-col :span="6" style="text-align: right;">
            <el-button type="danger" :disabled="selectedTasks.length === 0" @click="batchDelete">
              批量删除 ({{ selectedTasks.length }})
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 任务表格 -->
      <el-table
        :data="filteredTasks"
        style="width: 100%; min-width: 1200px;"
        @selection-change="handleSelectionChange"
        v-loading="loading"
        stripe
        border
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="id" label="任务ID" width="80" align="center" />
        
        <el-table-column prop="name" label="任务名称" min-width="220">
          <template #default="scope">
            <div class="task-name">
              <el-icon v-if="scope.row.type === 'video'"><VideoPlay /></el-icon>
              <el-icon v-else><VideoCamera /></el-icon>
              <span>{{ scope.row.name }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="type" label="类型" width="110" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.type === 'video' ? 'primary' : 'success'" size="small">
              {{ scope.row.type === 'video' ? '视频检测' : '实时监控' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="110" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="progress" label="进度" width="130" align="center">
          <template #default="scope">
            <el-progress 
              v-if="scope.row.status === 'processing'"
              :percentage="scope.row.progress" 
              :stroke-width="6"
              :show-text="false"
            />
            <span v-else-if="scope.row.status === 'completed'">100%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="detections" label="检测数" width="90" align="center" />
        
        <el-table-column prop="alerts" label="报警数" width="90" align="center">
          <template #default="scope">
            <span :class="{ 'alert-count': scope.row.alerts > 0 }">
              {{ scope.row.alerts }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="createTime" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.createTime) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="280" align="center">
          <template #default="scope">
            <div class="action-buttons">
              <el-button 
                v-if="scope.row.status === 'completed'"
                type="primary" 
                size="small"
                @click="viewResults(scope.row)"
              >
                查看结果
              </el-button>
              
              <el-button 
                v-if="scope.row.status === 'processing'"
                type="warning" 
                size="small"
                @click="pauseTask(scope.row)"
              >
                暂停
              </el-button>
              
              <el-button 
                v-if="scope.row.status === 'paused'"
                type="success" 
                size="small"
                @click="resumeTask(scope.row)"
              >
                继续
              </el-button>
              
              <el-button 
                v-if="['processing', 'paused'].includes(scope.row.status)"
                type="danger" 
                size="small"
                @click="stopTask(scope.row)"
              >
                停止
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个任务吗？"
                @confirm="deleteTask(scope.row)"
              >
                <template #reference>
                  <el-button 
                    type="danger" 
                    size="small"
                  >
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalTasks"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="showTaskDialog"
      :title="`任务详情 - ${currentTask?.name}`"
      width="80%"
      :before-close="handleTaskDialogClose"
    >
      <div v-if="currentTask" class="task-detail">
        <!-- 基本信息 -->
        <el-descriptions title="基本信息" :column="2" border>
          <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
          <el-descriptions-item label="任务名称">{{ currentTask.name }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ currentTask.type === 'video' ? '视频检测' : '实时监控' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentTask.status)">
              {{ getStatusText(currentTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(currentTask.createTime) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ currentTask.endTime ? formatDateTime(currentTask.endTime) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="处理耗时">
            {{ currentTask.duration ? formatDuration(currentTask.duration) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ currentTask.fileSize ? formatFileSize(currentTask.fileSize) : '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 检测配置 -->
        <el-descriptions title="检测配置" :column="2" border style="margin-top: 20px;">
          <el-descriptions-item label="置信度">{{ currentTask.config?.confidence || '-' }}</el-descriptions-item>
          <el-descriptions-item label="输入尺寸">{{ currentTask.config?.inputSize || '-' }}</el-descriptions-item>
          <el-descriptions-item label="设备类型">{{ currentTask.config?.device || '-' }}</el-descriptions-item>
          <el-descriptions-item label="报警行为">
            <el-tag 
              v-for="behavior in currentTask.config?.alertBehaviors || []" 
              :key="behavior"
              size="small"
              style="margin-right: 4px;"
            >
              {{ behavior }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 检测结果统计 -->
        <div v-if="currentTask.status === 'completed'" class="result-stats" style="margin-top: 20px;">
          <h4>检测结果统计</h4>
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentTask.totalFrames || 0 }}</div>
                <div class="stat-label">总帧数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentTask.detections || 0 }}</div>
                <div class="stat-label">检测总数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentTask.alerts || 0 }}</div>
                <div class="stat-label">报警次数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentTask.avgConfidence || 0 }}%</div>
                <div class="stat-label">平均置信度</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 日志信息 -->
        <div class="task-logs" style="margin-top: 20px;">
          <h4>处理日志</h4>
          <el-input
            v-model="taskLogs"
            type="textarea"
            :rows="10"
            readonly
            placeholder="暂无日志信息"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="showTaskDialog = false">关闭</el-button>
        <el-button 
          v-if="currentTask?.status === 'completed'" 
          type="primary" 
          @click="downloadResults"
        >
          下载结果
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  List, Loading, Check, Close, Refresh, Search, VideoPlay, VideoCamera 
} from '@element-plus/icons-vue'
import { getTasks, getTask, apiRequest, API_BASE_URL } from '@/utils/api'

export default {
  name: 'TaskManager',
  components: {
    List, Loading, Check, Close, Refresh, Search, VideoPlay, VideoCamera
  },
  setup() {
    const loading = ref(false)
    const tasks = ref([])
    const selectedTasks = ref([])
    const showTaskDialog = ref(false)
    const currentTask = ref(null)
    const taskLogs = ref('')
    
    // 搜索和筛选
    const searchKeyword = ref('')
    const currentFilter = ref('all')
    const typeFilter = ref('')
    const dateRange = ref([])
    
    // 分页
    const currentPage = ref(1)
    const pageSize = ref(20)
    const totalTasks = ref(0)
    
    // 统计数据
    const taskStats = reactive({
      total: 0,
      running: 0,
      completed: 0,
      failed: 0
    })
    
    // 状态筛选选项
    const statusFilters = [
      { label: '全部', value: 'all' },
      { label: '运行中', value: 'processing' },
      { label: '已完成', value: 'completed' },
      { label: '失败', value: 'failed' },
      { label: '暂停', value: 'paused' }
    ]

    // 过滤后的任务列表
    const filteredTasks = computed(() => {
      let filtered = tasks.value
      
      // 状态筛选
      if (currentFilter.value !== 'all') {
        filtered = filtered.filter(task => task.status === currentFilter.value)
      }
      
      // 类型筛选
      if (typeFilter.value) {
        filtered = filtered.filter(task => task.type === typeFilter.value)
      }
      
      // 关键词搜索
      if (searchKeyword.value) {
        const keyword = searchKeyword.value.toLowerCase()
        filtered = filtered.filter(task => 
          task.name.toLowerCase().includes(keyword) ||
          task.filename?.toLowerCase().includes(keyword)
        )
      }
      
      // 日期筛选
      if (dateRange.value && dateRange.value.length === 2) {
        const [startDate, endDate] = dateRange.value
        filtered = filtered.filter(task => {
          const taskDate = new Date(task.createTime)
          return taskDate >= startDate && taskDate <= endDate
        })
      }
      
      return filtered
    })

    // 获取任务列表 - 使用统一API方法
    const fetchTasks = async () => {
      loading.value = true
      try {
        const params = {
          page: currentPage.value,
          per_page: pageSize.value
        }
        
        const data = await getTasks(params)
        // 映射后端数据格式到前端期望格式
        tasks.value = (data.tasks || []).map(task => ({
          id: task.id,
          name: task.filename,
          type: task.source_type || 'video',
          status: task.status,
          progress: task.progress,
          detections: task.detections,
          alerts: 0, // 暂时设为0，后续可从单独API获取
          createTime: task.uploadTime,
          size: task.size
        }))
        totalTasks.value = data.total || 0
        
        // 更新统计数据
        updateStats()
        
        console.log('✓ 任务列表获取成功:', data)
      } catch (error) {
        console.error('获取任务列表失败:', error)
        ElMessage.error('获取任务列表失败')
      } finally {
        loading.value = false
      }
    }

    // 更新统计数据
    const updateStats = () => {
      taskStats.total = tasks.value.length
      taskStats.running = tasks.value.filter(t => t.status === 'processing').length
      taskStats.completed = tasks.value.filter(t => t.status === 'completed').length
      taskStats.failed = tasks.value.filter(t => t.status === 'failed').length
    }

    // 刷新任务列表
    const refreshTasks = () => {
      fetchTasks()
    }

    // 搜索处理
    const handleSearch = () => {
      // 搜索逻辑已在计算属性中实现
    }

    // 日期变化处理
    const handleDateChange = () => {
      // 日期筛选逻辑已在计算属性中实现
    }

    // 选择变化处理
    const handleSelectionChange = (selection) => {
      selectedTasks.value = selection
    }

    // 分页处理
    const handleSizeChange = (size) => {
      pageSize.value = size
      fetchTasks()
    }

    const handleCurrentChange = (page) => {
      currentPage.value = page
      fetchTasks()
    }

    // 查看任务结果 - 使用统一API方法
    const viewResults = async (task) => {
      try {
        // 获取任务详细结果
        const data = await apiRequest(`/api/tasks/${task.id}/results`)
        
        if (data.success) {
          // 更新当前任务信息，合并API返回的数据
          currentTask.value = {
            ...task,
            totalFrames: data.totalFrames,
            detections: data.totalDetections,
            alerts: data.alertCount,
            behaviors: data.behaviors,
            videoUrl: data.videoUrl,
            downloadUrl: data.downloadUrl
          }
          
          // 生成日志信息显示
          const logLines = [
            `任务 ${task.id} 处理完成`,
            `文件名: ${data.filename}`,
            `总帧数: ${data.totalFrames}`,
            `检测帧数: ${data.detectedFrames}`,
            `检测总数: ${data.totalDetections}`,
            `报警次数: ${data.alertCount}`,
            ''
          ]
          
          if (data.behaviors && data.behaviors.length > 0) {
            logLines.push('检测到的行为:')
            data.behaviors.forEach(behavior => {
              logLines.push(`- ${behavior.behavior}: ${behavior.count}次 (置信度: ${behavior.confidence}, 持续: ${behavior.duration})`)
            })
          } else {
            logLines.push('未检测到特定行为')
          }
          
          taskLogs.value = logLines.join('\n')
          showTaskDialog.value = true
        } else {
          ElMessage.error(data.error || '获取任务结果失败')
        }
      } catch (error) {
        console.error('获取任务详情失败:', error)
        ElMessage.error('获取任务详情失败')
      }
    }

    // 暂停任务 - 使用统一API方法
    const pauseTask = async (task) => {
      try {
        await apiRequest(`/api/tasks/${task.id}/pause`, {
          method: 'POST'
        })
        
        ElMessage.success('任务已暂停')
        fetchTasks()
      } catch (error) {
        console.error('暂停任务失败:', error)
        ElMessage.error('暂停任务失败')
      }
    }

    // 继续任务 - 使用统一API方法
    const resumeTask = async (task) => {
      try {
        await apiRequest(`/api/tasks/${task.id}/resume`, {
          method: 'POST'
        })
        
        ElMessage.success('任务已继续')
        fetchTasks()
      } catch (error) {
        console.error('继续任务失败:', error)
        ElMessage.error('继续任务失败')
      }
    }

    // 停止任务 - 使用统一API方法
    const stopTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要停止这个任务吗？', '确认停止', {
          type: 'warning'
        })
        
        await apiRequest(`/api/tasks/${task.id}/stop`, {
          method: 'POST'
        })
        
        ElMessage.success('任务已停止')
        fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('停止任务失败:', error)
          ElMessage.error('停止任务失败')
        }
      }
    }

    // 删除任务 - 使用统一API方法
    const deleteTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要删除这个任务吗？', '确认删除', {
          type: 'warning'
        })
        
        await apiRequest(`/api/tasks/${task.id}`, {
          method: 'DELETE'
        })
        
        ElMessage.success('任务已删除')
        fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除任务失败:', error)
          ElMessage.error('删除任务失败')
        }
      }
    }

    // 批量删除 - 使用统一API方法
    const batchDelete = async () => {
      try {
        await ElMessageBox.confirm(`确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`, '确认批量删除', {
          type: 'warning'
        })
        
        const taskIds = selectedTasks.value.map(task => task.id)
        await apiRequest('/api/tasks/batch-delete', {
          method: 'POST',
          body: JSON.stringify({ taskIds })
        })
        
        ElMessage.success('批量删除成功')
        selectedTasks.value = []
        fetchTasks()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量删除失败:', error)
          ElMessage.error('批量删除失败')
        }
      }
    }

    // 下载结果 - 使用统一API配置
    const downloadResults = () => {
      if (currentTask.value) {
        const link = document.createElement('a')
        link.href = `${API_BASE_URL}/api/download/result/${currentTask.value.id}`
        link.download = `results_${currentTask.value.name}`
        link.click()
      }
    }

    // 关闭任务对话框
    const handleTaskDialogClose = () => {
      showTaskDialog.value = false
      currentTask.value = null
      taskLogs.value = ''
    }

    // 获取状态类型
    const getStatusType = (status) => {
      const typeMap = {
        'pending': 'info',
        'processing': 'warning', 
        'running': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'stopped': 'info',
        'paused': 'warning'
      }
      return typeMap[status] || 'info'
    }

    // 获取状态文本
    const getStatusText = (status) => {
      const textMap = {
        'pending': '待处理',
        'processing': '处理中',
        'running': '运行中', 
        'completed': '已完成',
        'failed': '失败',
        'stopped': '已停止',
        'paused': '已暂停'
      }
      return textMap[status] || status
    }

    // 格式化日期时间
    const formatDateTime = (dateStr) => {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    const formatDuration = (seconds) => {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      const secs = seconds % 60
      
      if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`
      } else if (minutes > 0) {
        return `${minutes}m ${secs}s`
      } else {
        return `${secs}s`
      }
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    onMounted(() => {
      fetchTasks()
    })

    return {
      loading,
      tasks,
      selectedTasks,
      showTaskDialog,
      currentTask,
      taskLogs,
      searchKeyword,
      currentFilter,
      typeFilter,
      dateRange,
      currentPage,
      pageSize,
      totalTasks,
      taskStats,
      statusFilters,
      filteredTasks,
      fetchTasks,
      refreshTasks,
      handleSearch,
      handleDateChange,
      handleSelectionChange,
      handleSizeChange,
      handleCurrentChange,
      viewResults,
      pauseTask,
      resumeTask,
      stopTask,
      deleteTask,
      batchDelete,
      downloadResults,
      handleTaskDialogClose,
      getStatusType,
      getStatusText,
      formatDateTime,
      formatDuration,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.task-manager {
  padding: 20px;
  background: #f8f9fa;
  min-height: 100vh;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.total {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.stat-icon.running {
  background: linear-gradient(135deg, #e6a23c, #f0a020);
}

.stat-icon.completed {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.stat-icon.failed {
  background: linear-gradient(135deg, #f56c6c, #f78989);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.task-list-card {
  margin-bottom: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow-x: auto;
}

.task-list-card .el-card__body {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0;
  margin-bottom: 16px;
}

.card-header span {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
}

.filter-section .el-input,
.filter-section .el-select,
.filter-section .el-date-picker {
  height: 36px;
  line-height: 36px;
}

.filter-section .el-input__wrapper,
.filter-section .el-select__wrapper {
  min-height: 36px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-start;
  align-items: center;
  min-height: 32px;
}

.action-buttons .el-button {
  margin: 0;
  min-width: auto;
  padding: 4px 8px;
  white-space: nowrap;
}

.task-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-count {
  color: #f56c6c;
  font-weight: bold;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.task-detail {
  padding: 20px 0;
}

.result-stats {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.result-stats h4 {
  margin: 0 0 16px 0;
  color: #303133;
}

.stat-item {
  text-align: center;
}

.stat-item .stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-item .stat-label {
  font-size: 12px;
  color: #909399;
}

.task-logs h4 {
  margin: 0 0 12px 0;
  color: #303133;
}

/* 表格滚动容器 */
.task-list-card .el-table {
  border-radius: 6px;
  overflow: hidden;
}

.task-list-card .el-table__header-wrapper {
  border-radius: 6px 6px 0 0;
}

.task-list-card .el-table__body-wrapper {
  max-height: 600px;
  overflow-y: auto;
}

/* 确保表格在小屏幕上的表现 */
@media (max-width: 1400px) {
  .task-list-card {
    overflow-x: auto;
  }
  
  .task-list-card .el-table {
    min-width: 1200px;
  }
}

/* 操作按钮优化 */
.action-buttons .el-button + .el-button {
  margin-left: 0;
}

.action-buttons .el-popconfirm {
  display: inline-block;
}

/* 防止搜索框重叠的样式 */
.filter-section {
  position: relative;
  z-index: 1;
  clear: both;
}

.filter-section .el-row {
  align-items: center;
}

.filter-section .el-col {
  margin-bottom: 0;
}
</style> 