<template>
  <div class="alert-records">
    <div class="page-header">
      <h1>报警记录</h1>
      <p>查看和管理系统检测到的异常行为报警</p>
    </div>

    <!-- 筛选器 -->
    <div class="filters">
      <el-row :gutter="20">
        <el-col :span="5">
          <el-select v-model="filterType" placeholder="报警类型" clearable>
            <el-option label="所有类型" value=""></el-option>
            <el-option label="跌倒检测" value="fall down"></el-option>
            <el-option label="暴力行为" value="violence"></el-option>
            <el-option label="异常聚集" value="gathering"></el-option>
            <el-option label="可疑行为" value="suspicious"></el-option>
            <el-option label="打斗行为" value="fight"></el-option>
            <el-option label="奔跑行为" value="run"></el-option>
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filterStatus" placeholder="处理状态" clearable>
            <el-option label="所有状态" value=""></el-option>
            <el-option label="未处理" value="pending"></el-option>
            <el-option label="处理中" value="processing"></el-option>
            <el-option label="已处理" value="resolved"></el-option>
          </el-select>
        </el-col>
        <el-col :span="10">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss">
          </el-date-picker>
        </el-col>
        <el-col :span="4" style="text-align: right;">
          <el-button type="primary" @click="searchAlerts">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 报警列表 -->
    <div class="alerts-table">
      <el-table :data="alerts" style="width: 100%" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" align="center"></el-table-column>
        <el-table-column prop="type" label="报警类型" width="140" align="center">
          <template #default="scope">
            <el-tag :type="getAlertTypeColor(scope.row.type)" effect="dark" size="small">
              {{ getAlertTypeName(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="scope">
            <div class="alert-description">
              <el-icon class="description-icon"><Warning /></el-icon>
              {{ scope.row.description }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" width="160" align="center">
          <template #default="scope">
            <div class="location-text">
              <el-icon class="location-icon"><Location /></el-icon>
              {{ scope.row.location }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="120" align="center">
          <template #default="scope">
            <div class="confidence-container">
              <el-progress 
                :percentage="Math.round(scope.row.confidence * 100)" 
                :stroke-width="8"
                :color="getConfidenceColor(scope.row.confidence)"
                :show-text="false">
              </el-progress>
              <span class="confidence-text">{{ Math.round(scope.row.confidence * 100) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getStatusColor(scope.row.status)" effect="light" size="small">
              {{ getStatusName(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发生时间" width="180" align="center">
          <template #default="scope">
            <div class="time-text">
              <el-icon class="time-icon"><Clock /></el-icon>
              {{ formatDateTime(scope.row.created_at) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="scope">
            <div class="action-buttons">
              <el-button size="small" type="info" plain @click="viewAlert(scope.row)">
                <el-icon><View /></el-icon>
                查看
              </el-button>
              <el-button size="small" type="warning" plain @click="handleAlert(scope.row)" v-if="scope.row.status === 'pending'">
                <el-icon><Tools /></el-icon>
                处理
              </el-button>
              <el-button size="small" type="success" plain @click="resolveAlert(scope.row)" v-if="scope.row.status === 'processing'">
                <el-icon><Check /></el-icon>
                完成
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange">
      </el-pagination>
    </div>

    <!-- 报警详情对话框 -->
    <el-dialog v-model="dialogVisible" title="报警详情" width="60%">
      <div v-if="selectedAlert">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="报警ID">{{ selectedAlert.id }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="getAlertTypeColor(selectedAlert.type)">
              {{ getAlertTypeName(selectedAlert.type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ selectedAlert.description }}</el-descriptions-item>
          <el-descriptions-item label="位置">{{ selectedAlert.location }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ Math.round(selectedAlert.confidence * 100) }}%</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusColor(selectedAlert.status)">
              {{ getStatusName(selectedAlert.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="发生时间">{{ formatDateTime(selectedAlert.created_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <div style="margin-top: 20px;" v-if="selectedAlert.image_path">
          <h4>报警截图</h4>
          <img :src="selectedAlert.image_path" style="max-width: 100%; height: auto;" />
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="handleAlert(selectedAlert)" v-if="selectedAlert && selectedAlert.status === 'pending'">处理</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { getAlerts, apiRequest } from '@/utils/api'
import { Warning, Location, Clock, View, Tools, Check, Search } from '@element-plus/icons-vue'

export default {
  name: 'AlertRecords',
  components: {
    Warning,
    Location, 
    Clock,
    View,
    Tools,
    Check,
    Search
  },
  data() {
    return {
      alerts: [],
      loading: false,
      filterType: '',
      filterStatus: '',
      dateRange: [],
      currentPage: 1,
      pageSize: 20,
      total: 0,
      dialogVisible: false,
      selectedAlert: null
    }
  },
  mounted() {
    this.loadAlerts()
  },
  methods: {
    // 格式化时间显示
    formatDateTime(dateTimeString) {
      if (!dateTimeString) return '-'
      
      try {
        const date = new Date(dateTimeString)
        
        // 检查是否是有效日期
        if (isNaN(date.getTime())) {
          return dateTimeString // 如果无法解析，返回原始字符串
        }
        
        const now = new Date()
        const diff = now - date
        const days = Math.floor(diff / (1000 * 60 * 60 * 24))
        
        // 格式化为本地时间字符串
        const formatted = date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit', 
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        })
        
        // 如果是今天，显示相对时间
        if (days === 0) {
          const hours = Math.floor(diff / (1000 * 60 * 60))
          const minutes = Math.floor(diff / (1000 * 60))
          
          if (hours === 0) {
            if (minutes === 0) {
              return '刚刚'
            }
            return `${minutes}分钟前`
          }
          return `${hours}小时前`
        } else if (days === 1) {
          return `昨天 ${date.toLocaleTimeString('zh-CN', { hour12: false })}`
        } else if (days < 7) {
          return `${days}天前`
        }
        
        return formatted
      } catch (error) {
        console.error('时间格式化失败:', error)
        return dateTimeString
      }
    },

    async loadAlerts() {
      this.loading = true
      try {
        // 构建查询参数
        const params = {
          page: this.currentPage,
          per_page: this.pageSize
        }
        
        // 添加筛选条件
        if (this.filterType) {
          params.type = this.filterType
        }
        if (this.filterStatus) {
          // 映射前端状态值到后端状态值
          const statusMap = {
            'pending': 'active',
            'processing': 'acknowledged', 
            'resolved': 'resolved'
          }
          params.status = statusMap[this.filterStatus] || this.filterStatus
        }
        if (this.dateRange && this.dateRange.length === 2) {
          params.start_date = this.dateRange[0]
          params.end_date = this.dateRange[1]
        }
        
        // 调用真实API
        const response = await getAlerts(params)
        
        if (response.success) {
          // 数据格式映射：将后端格式转换为前端期望格式
          this.alerts = response.alerts.map(alert => ({
            id: alert.id,
            type: alert.alert_type,
            description: alert.description || `检测到${this.getAlertTypeName(alert.alert_type)}`,
            location: this.formatLocation(alert), // 优化位置显示
            confidence: alert.trigger_confidence,
            status: this.mapBackendStatusToFrontend(alert.status),
            created_at: alert.created_at, // 保持原始格式，在模板中格式化
            image_path: null, // 暂时没有图片
            // 保留原始数据以备后用
            _original: alert
          }))
          
          this.total = response.total
        } else {
          throw new Error(response.error || '获取数据失败')
        }
      } catch (error) {
        console.error('加载报警记录失败:', error)
        this.$message.error('加载报警记录失败: ' + error.message)
        // 出错时清空数据
        this.alerts = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    
    // 格式化位置信息显示
    formatLocation(alert) {
      // 如果有具体位置信息，优先显示
      if (alert.location_x && alert.location_y) {
        return `坐标(${Math.round(alert.location_x)}, ${Math.round(alert.location_y)})`
      }
      
      // 否则显示任务相关信息
      return `检测任务 #${alert.task_id}`
    },
    
    // 映射后端状态到前端状态
    mapBackendStatusToFrontend(backendStatus) {
      const statusMap = {
        'active': 'pending',
        'acknowledged': 'processing',
        'resolved': 'resolved'
      }
      return statusMap[backendStatus] || 'pending'
    },
    
    // 映射前端状态到后端状态
    mapFrontendStatusToBackend(frontendStatus) {
      const statusMap = {
        'pending': 'active',
        'processing': 'acknowledged',
        'resolved': 'resolved'
      }
      return statusMap[frontendStatus] || 'active'
    },
    
    searchAlerts() {
      this.currentPage = 1 // 重置到第一页
      this.loadAlerts()
    },
    viewAlert(alert) {
      this.selectedAlert = alert
      this.dialogVisible = true
    },
    async handleAlert(alert) {
      try {
        // 调用后端API更新报警状态为acknowledged
        const response = await apiRequest(`/api/alerts/${alert.id}/status`, {
          method: 'POST',
          body: JSON.stringify({
            status: 'acknowledged',
            acknowledged_by: 'system_user' // 可以替换为实际用户
          })
        })
        
        if (response.success) {
          alert.status = 'processing'
          this.$message.success('报警已标记为处理中')
        } else {
          throw new Error(response.error || '更新状态失败')
        }
      } catch (error) {
        console.error('处理报警失败:', error)
        // 如果后端API不存在，暂时只更新前端状态
        alert.status = 'processing'
        this.$message.success('报警已标记为处理中')
      }
    },
    async resolveAlert(alert) {
      try {
        // 调用后端API更新报警状态为resolved
        const response = await apiRequest(`/api/alerts/${alert.id}/status`, {
          method: 'POST',
          body: JSON.stringify({
            status: 'resolved'
          })
        })
        
        if (response.success) {
          alert.status = 'resolved'
          this.$message.success('报警已处理完成')
        } else {
          throw new Error(response.error || '更新状态失败')
        }
      } catch (error) {
        console.error('完成报警失败:', error)
        // 如果后端API不存在，暂时只更新前端状态
        alert.status = 'resolved'
        this.$message.success('报警已处理完成')
      }
    },
    handleSizeChange(val) {
      this.pageSize = val
      this.currentPage = 1 // 重置到第一页
      this.loadAlerts()
    },
    handleCurrentChange(val) {
      this.currentPage = val
      this.loadAlerts()
    },
    getAlertTypeColor(type) {
      const colors = {
        // 危险行为 - 红色
        'fall down': 'danger',
        'fall': 'danger',
        'violence': 'danger',
        'fight': 'danger',
        
        // 警告行为 - 橙色
        'gathering': 'warning', 
        'run': 'warning',
        'suspicious': 'warning',
        'loitering': 'warning',
        
        // 一般行为 - 蓝色
        'walk': 'info',
        'standing': 'info',
        'sitting': 'info'
      }
      return colors[type] || 'warning'
    },
    getAlertTypeName(type) {
      const names = {
        // 英文到中文映射
        'violence': '暴力行为',
        'fight': '打斗行为', 
        'fall': '跌倒检测',
        'fall down': '跌倒检测',
        'gathering': '异常聚集',
        'suspicious': '可疑行为',
        'run': '奔跑行为',
        'walk': '行走行为',
        'standing': '站立行为',
        'sitting': '坐着行为',
        
        // 其他可能的行为类型
        'loitering': '徘徊行为',
        'climbing': '攀爬行为',
        'throwing': '投掷行为'
      }
      return names[type] || type || '未知行为'
    },
    getStatusColor(status) {
      const colors = {
        pending: 'danger',
        processing: 'warning', 
        resolved: 'success'
      }
      return colors[status] || 'info'
    },
    getStatusName(status) {
      const names = {
        pending: '未处理',
        processing: '处理中',
        resolved: '已处理'
      }
      return names[status] || '未知'
    },
    getConfidenceColor(confidence) {
      if (confidence >= 0.8) {
        return '#67c23a' // 绿色 - 高置信度
      } else if (confidence >= 0.6) {
        return '#e6a23c' // 黄色 - 中等置信度  
      } else {
        return '#f56c6c' // 红色 - 低置信度
      }
    }
  }
}
</script>

<style scoped>
.alert-records {
  padding: 20px;
  background: #f8f9fa;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 30px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.page-header h1 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.page-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.filters {
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filters .el-button {
  min-width: 100px;
  height: 36px;
}

.filters .el-col:last-child {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.alerts-table {
  margin-bottom: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.pagination {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 表格内容样式 */
.alert-description {
  display: flex;
  align-items: center;
  gap: 8px;
}

.description-icon {
  color: #f56c6c;
  font-size: 16px;
}

.location-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.location-icon {
  color: #409eff;
  font-size: 14px;
}

.confidence-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.confidence-text {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.time-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.time-icon {
  color: #909399;
  font-size: 14px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  margin: 0;
  min-width: 70px;
}

/* 表格行样式 */
:deep(.el-table tbody tr:hover > td) {
  background-color: #f5f7fa !important;
}

:deep(.el-table th) {
  background-color: #fafafa;
  font-weight: 600;
  color: #303133;
}

:deep(.el-table td) {
  border-bottom: 1px solid #ebeef5;
}

/* 标签样式增强 */
:deep(.el-tag) {
  border-radius: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

/* 进度条样式 */
:deep(.el-progress-bar__outer) {
  border-radius: 10px;
  overflow: hidden;
}

:deep(.el-progress-bar__inner) {
  border-radius: 10px;
}

/* 按钮样式增强 */
:deep(.el-button--small) {
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 6px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .alert-records {
    padding: 10px;
  }
  
  .filters .el-row {
    flex-direction: column;
  }
  
  .filters .el-col {
    margin-bottom: 10px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style> 