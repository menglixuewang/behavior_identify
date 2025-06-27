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
          <el-col :span="8">
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
            <el-select v-model="typeFilter" placeholder="任务类型" clearable>
              <el-option label="视频检测" value="video" />
              <el-option label="实时监控" value="realtime" />
            </el-select>
          </el-col>
          
          <el-col :span="6">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              size="default"
              @change="handleDateChange"
            />
          </el-col>
          
          <el-col :span="6">
            <el-button type="danger" :disabled="selectedTasks.length === 0" @click="batchDelete">
              批量删除 ({{ selectedTasks.length }})
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 任务表格 -->
      <el-table
        :data="filteredTasks"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        v-loading="loading"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="id" label="任务ID" width="80" />
        
        <el-table-column prop="name" label="任务名称" min-width="200">
          <template #default="scope">
            <div class="task-name">
              <el-icon v-if="scope.row.type === 'video'"><VideoPlay /></el-icon>
              <el-icon v-else><VideoCamera /></el-icon>
              <span>{{ scope.row.name }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.type === 'video' ? 'primary' : 'success'" size="small">
              {{ scope.row.type === 'video' ? '视频检测' : '实时监控' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="progress" label="进度" width="120">
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
        
        <el-table-column prop="detections" label="检测数" width="80" />
        
        <el-table-column prop="alerts" label="报警数" width="80">
          <template #default="scope">
            <span :class="{ 'alert-count': scope.row.alerts > 0 }">
              {{ scope.row.alerts }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="createTime" label="创建时间" width="160">
          <template #default="scope">
            {{ formatDateTime(scope.row.createTime) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button-group>
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
              
              <el-button 
                type="danger" 
                size="small"
                @click="deleteTask(scope.row)"
              >
                删除
              </el-button>
            </el-button-group>
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

    // 获取任务列表
    const fetchTasks = async () => {
      loading.value = true
      try {
        const response = await fetch(`/api/tasks?page=${currentPage.value}&size=${pageSize.value}`)
        if (response.ok) {
          const data = await response.json()
          tasks.value = data.tasks || []
          totalTasks.value = data.total || 0
          
          // 更新统计数据
          updateStats()
        }
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

    // 查看任务结果
    const viewResults = async (task) => {
      try {
        const response = await fetch(`/api/tasks/${task.id}/logs`)
        if (response.ok) {
          const data = await response.json()
          taskLogs.value = data.logs || '暂无日志信息'
        }
        
        currentTask.value = task
        showTaskDialog.value = true
      } catch (error) {
        console.error('获取任务详情失败:', error)
        ElMessage.error('获取任务详情失败')
      }
    }

    // 暂停任务
    const pauseTask = async (task) => {
      try {
        const response = await fetch(`/api/tasks/${task.id}/pause`, {
          method: 'POST'
        })
        
        if (response.ok) {
          ElMessage.success('任务已暂停')
          fetchTasks()
        } else {
          ElMessage.error('暂停任务失败')
        }
      } catch (error) {
        ElMessage.error('暂停任务失败')
      }
    }

    // 继续任务
    const resumeTask = async (task) => {
      try {
        const response = await fetch(`/api/tasks/${task.id}/resume`, {
          method: 'POST'
        })
        
        if (response.ok) {
          ElMessage.success('任务已继续')
          fetchTasks()
        } else {
          ElMessage.error('继续任务失败')
        }
      } catch (error) {
        ElMessage.error('继续任务失败')
      }
    }

    // 停止任务
    const stopTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要停止这个任务吗？', '确认停止', {
          type: 'warning'
        })
        
        const response = await fetch(`/api/tasks/${task.id}/stop`, {
          method: 'POST'
        })
        
        if (response.ok) {
          ElMessage.success('任务已停止')
          fetchTasks()
        } else {
          ElMessage.error('停止任务失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('停止任务失败')
        }
      }
    }

    // 删除任务
    const deleteTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要删除这个任务吗？', '确认删除', {
          type: 'warning'
        })
        
        const response = await fetch(`/api/tasks/${task.id}`, {
          method: 'DELETE'
        })
        
        if (response.ok) {
          ElMessage.success('任务已删除')
          fetchTasks()
        } else {
          ElMessage.error('删除任务失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除任务失败')
        }
      }
    }

    // 批量删除
    const batchDelete = async () => {
      try {
        await ElMessageBox.confirm(`确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`, '确认批量删除', {
          type: 'warning'
        })
        
        const taskIds = selectedTasks.value.map(task => task.id)
        const response = await fetch('/api/tasks/batch-delete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ taskIds })
        })
        
        if (response.ok) {
          ElMessage.success('批量删除成功')
          selectedTasks.value = []
          fetchTasks()
        } else {
          ElMessage.error('批量删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('批量删除失败')
        }
      }
    }

    // 下载结果
    const downloadResults = () => {
      if (currentTask.value) {
        const link = document.createElement('a')
        link.href = `/api/tasks/${currentTask.value.id}/download`
        link.download = `results_${currentTask.value.name}`
        link.click()
      }
    }

    // 关闭任务详情对话框
    const handleTaskDialogClose = () => {
      showTaskDialog.value = false
      currentTask.value = null
      taskLogs.value = ''
    }

    // 工具函数
    const getStatusType = (status) => {
      const typeMap = {
        'pending': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'paused': 'info'
      }
      return typeMap[status] || 'info'
    }

    const getStatusText = (status) => {
      const textMap = {
        'pending': '等待中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败',
        'paused': '已暂停'
      }
      return textMap[status] || '未知'
    }

    const formatDateTime = (timestamp) => {
      return new Date(timestamp).toLocaleString()
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
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
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
</style> 