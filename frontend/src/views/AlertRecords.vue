<template>
  <div class="alert-records">
    <div class="page-header">
      <h1>报警记录</h1>
      <p>查看和管理系统检测到的异常行为报警</p>
    </div>

    <!-- 筛选器 -->
    <div class="filters">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select v-model="filterType" placeholder="报警类型" clearable>
            <el-option label="所有类型" value=""></el-option>
            <el-option label="暴力行为" value="violence"></el-option>
            <el-option label="异常聚集" value="gathering"></el-option>
            <el-option label="可疑行为" value="suspicious"></el-option>
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterStatus" placeholder="处理状态" clearable>
            <el-option label="所有状态" value=""></el-option>
            <el-option label="未处理" value="pending"></el-option>
            <el-option label="处理中" value="processing"></el-option>
            <el-option label="已处理" value="resolved"></el-option>
          </el-select>
        </el-col>
        <el-col :span="8">
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
        <el-col :span="4">
          <el-button type="primary" @click="searchAlerts">搜索</el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 报警列表 -->
    <div class="alerts-table">
      <el-table :data="alerts" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column prop="type" label="报警类型" width="120">
          <template #default="scope">
            <el-tag :type="getAlertTypeColor(scope.row.type)">
              {{ getAlertTypeName(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200"></el-table-column>
        <el-table-column prop="location" label="位置" width="120"></el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="scope">
            <el-progress :percentage="Math.round(scope.row.confidence * 100)" :stroke-width="6"></el-progress>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusColor(scope.row.status)">
              {{ getStatusName(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发生时间" width="180"></el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="viewAlert(scope.row)">查看</el-button>
            <el-button size="small" type="primary" @click="handleAlert(scope.row)" v-if="scope.row.status === 'pending'">处理</el-button>
            <el-button size="small" type="success" @click="resolveAlert(scope.row)" v-if="scope.row.status === 'processing'">完成</el-button>
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
          <el-descriptions-item label="发生时间">{{ selectedAlert.created_at }}</el-descriptions-item>
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
export default {
  name: 'AlertRecords',
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
    async loadAlerts() {
      this.loading = true
      try {
        // 模拟数据
        await new Promise(resolve => setTimeout(resolve, 1000))
        this.alerts = [
          {
            id: 1,
            type: 'violence',
            description: '检测到疑似暴力行为',
            location: '摄像头01',
            confidence: 0.89,
            status: 'pending',
            created_at: '2024-01-15 14:30:25',
            image_path: '/api/alerts/1/image'
          },
          {
            id: 2,
            type: 'gathering',
            description: '检测到异常人群聚集',
            location: '摄像头02',
            confidence: 0.76,
            status: 'processing',
            created_at: '2024-01-15 13:45:12',
            image_path: '/api/alerts/2/image'
          },
          {
            id: 3,
            type: 'suspicious',
            description: '检测到可疑徘徊行为',
            location: '摄像头03',
            confidence: 0.82,
            status: 'resolved',
            created_at: '2024-01-15 12:20:08',
            image_path: '/api/alerts/3/image'
          }
        ]
        this.total = this.alerts.length
      } catch (error) {
        this.$message.error('加载报警记录失败')
      } finally {
        this.loading = false
      }
    },
    searchAlerts() {
      this.loadAlerts()
    },
    viewAlert(alert) {
      this.selectedAlert = alert
      this.dialogVisible = true
    },
    async handleAlert(alert) {
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 500))
        alert.status = 'processing'
        this.$message.success('报警已标记为处理中')
      } catch (error) {
        this.$message.error('操作失败')
      }
    },
    async resolveAlert(alert) {
      try {
        // 模拟API调用
        await new Promise(resolve => setTimeout(resolve, 500))
        alert.status = 'resolved'
        this.$message.success('报警已处理完成')
      } catch (error) {
        this.$message.error('操作失败')
      }
    },
    handleSizeChange(val) {
      this.pageSize = val
      this.loadAlerts()
    },
    handleCurrentChange(val) {
      this.currentPage = val
      this.loadAlerts()
    },
    getAlertTypeColor(type) {
      const colors = {
        violence: 'danger',
        gathering: 'warning',
        suspicious: 'info'
      }
      return colors[type] || 'info'
    },
    getAlertTypeName(type) {
      const names = {
        violence: '暴力行为',
        gathering: '异常聚集',
        suspicious: '可疑行为'
      }
      return names[type] || '未知'
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
    }
  }
}
</script>

<style scoped>
.alert-records {
  padding: 20px;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  margin: 0 0 10px 0;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #909399;
}

.filters {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.alerts-table {
  margin-bottom: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style> 