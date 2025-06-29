<template>
  <div class="video-upload">
    <!-- 上传区域 -->
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>视频文件上传</span>
          <el-button 
            type="primary" 
            :disabled="!selectedFile || uploading"
            @click="startUpload"
          >
            {{ uploading ? '上传中...' : '开始上传' }}
          </el-button>
        </div>
      </template>

      <div class="upload-area">
        <el-upload
          ref="uploadRef"
          class="upload-dragger"
          drag
          :auto-upload="false"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :accept="'.mp4,.avi,.mov,.mkv,.flv,.wmv'"
          :limit="1"
        >
          <div class="upload-content">
            <el-icon class="upload-icon" size="48">
              <Upload />
            </el-icon>
            <div class="upload-text">
              <p>将视频文件拖拽到此处，或<em>点击上传</em></p>
              <p class="upload-hint">支持 MP4、AVI、MOV、MKV、FLV、WMV 格式</p>
            </div>
          </div>
        </el-upload>

        <!-- 文件信息 -->
        <div v-if="selectedFile" class="file-info">
          <div class="file-details">
            <div class="file-icon">
              <el-icon size="24"><VideoPlay /></el-icon>
            </div>
            <div class="file-content">
              <div class="file-name">{{ selectedFile.name }}</div>
              <div class="file-meta">
                <span>大小: {{ formatFileSize(selectedFile.size) }}</span>
                <span>格式: {{ getFileExtension(selectedFile.name) }}</span>
              </div>
            </div>
            <div class="file-actions">
              <el-button 
                type="danger" 
                size="small" 
                :icon="Delete"
                @click="removeFile"
              >
                移除
              </el-button>
            </div>
          </div>

          <!-- 上传进度 -->
          <div v-if="uploading" class="upload-progress">
            <el-progress 
              :percentage="uploadProgress" 
              :status="uploadStatus"
              :stroke-width="8"
            />
            <div class="progress-info">
              <span>{{ uploadStatusText }}</span>
              <span>{{ uploadProgress }}%</span>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 检测配置 -->
    <el-card class="config-card">
      <template #header>
        <span>检测配置</span>
      </template>

      <el-form :model="detectConfig" label-width="120px" class="config-form">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="检测置信度">
              <el-slider
                v-model="detectConfig.confidence"
                :min="0.1"
                :max="1.0"
                :step="0.05"
                show-stops
                show-input
                :input-size="'small'"
              />
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="输入尺寸">
              <el-select v-model="detectConfig.inputSize" placeholder="选择输入尺寸">
                <el-option label="416x416" :value="416" />
                <el-option label="640x640" :value="640" />
                <el-option label="832x832" :value="832" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="设备类型">
              <el-radio-group v-model="detectConfig.device">
                <el-radio label="cpu">CPU</el-radio>
                <el-radio label="cuda">GPU</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="输出格式">
              <el-select v-model="detectConfig.outputFormat" placeholder="选择输出格式">
                <el-option label="视频文件" value="video" />
                <el-option label="JSON数据" value="json" />
                <el-option label="视频+JSON" value="both" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="报警行为">
          <el-checkbox-group v-model="detectConfig.alertBehaviors">
            <el-checkbox label="fall down">跌倒</el-checkbox>
            <el-checkbox label="fight">打斗</el-checkbox>
            <el-checkbox label="enter">闯入</el-checkbox>
            <el-checkbox label="exit">离开</el-checkbox>
            <el-checkbox label="run">奔跑</el-checkbox>
            <el-checkbox label="sit">坐下</el-checkbox>
            <el-checkbox label="stand">站立</el-checkbox>
            <el-checkbox label="walk">行走</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="保存结果">
          <el-switch
            v-model="detectConfig.saveResults"
            active-text="保存到数据库"
            inactive-text="仅临时处理"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 处理历史 -->
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <span>处理历史</span>
          <el-button type="text" size="small" @click="refreshHistory">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="uploadHistory" style="width: 100%">
        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="scope">
            <div class="filename-cell">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ scope.row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="size" label="文件大小" width="120">
          <template #default="scope">
            {{ formatFileSize(scope.row.size) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag 
              :type="getStatusType(scope.row.status)"
              size="small"
            >
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="detections" label="检测数量" width="100">
          <template #default="scope">
            {{ scope.row.detections || '--' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="uploadTime" label="上传时间" width="160">
          <template #default="scope">
            {{ formatDateTime(scope.row.uploadTime) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button 
              type="primary" 
              size="small"
              :disabled="scope.row.status !== 'completed'"
              @click="viewResults(scope.row)"
            >
              查看结果
            </el-button>
            <el-button 
              type="danger" 
              size="small"
              @click="deleteRecord(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="uploadHistory.length === 0" class="empty-history">
        <el-icon size="48"><DocumentRemove /></el-icon>
        <p>暂无上传记录</p>
      </div>
    </el-card>

    <!-- 结果查看对话框 -->
    <el-dialog
      v-model="showResultDialog"
      title="检测结果"
      width="80%"
      :before-close="handleResultDialogClose"
    >
      <div v-if="currentResult" class="result-content">
        <!-- 结果视频 -->
        <div class="result-video">
          <video 
            :src="currentResult.videoUrl" 
            controls 
            style="width: 100%; max-height: 400px;"
          />
        </div>

        <!-- 检测统计 -->
        <div class="result-stats">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentResult.totalFrames }}</div>
                <div class="stat-label">总帧数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentResult.detectedFrames }}</div>
                <div class="stat-label">检测帧数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentResult.totalDetections }}</div>
                <div class="stat-label">检测总数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ currentResult.alertCount }}</div>
                <div class="stat-label">报警次数</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 行为分析 -->
        <div class="behavior-analysis">
          <h4>行为分析</h4>
          <el-table :data="currentResult.behaviors" size="small">
            <el-table-column prop="behavior" label="行为" />
            <el-table-column prop="count" label="检测次数" />
            <el-table-column prop="confidence" label="平均置信度" />
            <el-table-column prop="duration" label="持续时间" />
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button @click="showResultDialog = false">关闭</el-button>
        <el-button type="primary" @click="downloadResults">下载结果</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Upload, VideoPlay, Delete, Refresh, DocumentRemove 
} from '@element-plus/icons-vue'

export default {
  name: 'VideoUpload',
  components: {
    Upload, VideoPlay, Delete, Refresh, DocumentRemove
  },
  setup() {
    const uploadRef = ref(null)
    const selectedFile = ref(null)
    const uploading = ref(false)
    const uploadProgress = ref(0)
    const uploadStatus = ref('')
    const uploadStatusText = ref('')
    const uploadHistory = ref([])
    const showResultDialog = ref(false)
    const currentResult = ref(null)

    const detectConfig = reactive({
      confidence: 0.5,
      inputSize: 640,
      device: 'cpu',
      outputFormat: 'both',
      alertBehaviors: ['fall down', 'fight', 'enter'], // 默认只对最重要的三种异常行为报警
      saveResults: true
    })

    // 文件选择处理
    const handleFileChange = (file) => {
      selectedFile.value = file.raw
      validateFile(file.raw)
    }

    // 文件移除处理
    const handleFileRemove = () => {
      selectedFile.value = null
    }

    // 移除文件
    const removeFile = () => {
      selectedFile.value = null
      uploadRef.value.clearFiles()
    }

    // 验证文件
    const validateFile = (file) => {
      const maxSize = 500 * 1024 * 1024 // 500MB
      if (file.size > maxSize) {
        ElMessage.error('文件大小不能超过500MB')
        removeFile()
        return false
      }

      const allowedTypes = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
      const fileExt = '.' + file.name.split('.').pop().toLowerCase()
      if (!allowedTypes.includes(fileExt)) {
        ElMessage.error('不支持的文件格式')
        removeFile()
        return false
      }

      return true
    }

    // 开始上传
    const startUpload = async () => {
      if (!selectedFile.value) {
        ElMessage.error('请选择要上传的视频文件')
        return
      }

      uploading.value = true
      uploadProgress.value = 0
      uploadStatus.value = ''
      uploadStatusText.value = '准备上传...'

      // 添加调试信息：打印前端配置
      console.log('🔧 前端检测配置:', detectConfig)
      console.log('📤 准备上传文件:', {
        name: selectedFile.value.name,
        size: selectedFile.value.size,
        type: selectedFile.value.type
      })

      try {
        const formData = new FormData()
        formData.append('video', selectedFile.value)

        // 将配置参数分别添加到FormData中，而不是作为JSON字符串
        formData.append('confidence', detectConfig.confidence.toString())
        formData.append('input_size', detectConfig.inputSize.toString())
        formData.append('device', detectConfig.device)
        formData.append('output_format', detectConfig.outputFormat)
        formData.append('alert_behaviors', JSON.stringify(detectConfig.alertBehaviors))
        formData.append('save_results', detectConfig.saveResults.toString())

        console.log('📤 上传参数:', {
          confidence: detectConfig.confidence,
          input_size: detectConfig.inputSize,
          device: detectConfig.device,
          output_format: detectConfig.outputFormat,
          alert_behaviors: detectConfig.alertBehaviors,
          save_results: detectConfig.saveResults
        })

        const xhr = new XMLHttpRequest()
        
        // 上传进度
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            uploadProgress.value = Math.round((event.loaded / event.total) * 100)
            uploadStatusText.value = `上传中... ${uploadProgress.value}%`
          }
        }

        // 上传完成
        xhr.onload = () => {
          if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText)
            uploadStatusText.value = '上传完成，开始检测...'
            startDetection(response.taskId)
          } else {
            throw new Error('上传失败')
          }
        }

        // 上传错误
        xhr.onerror = () => {
          throw new Error('网络错误')
        }

        xhr.open('POST', 'http://localhost:5000/api/upload')
        xhr.send(formData)

      } catch (error) {
        ElMessage.error('上传失败: ' + error.message)
        uploading.value = false
        uploadStatus.value = 'exception'
        uploadStatusText.value = '上传失败'
      }
    }

    // 开始检测
    const startDetection = async (taskId) => {
      try {
        uploadStatusText.value = '检测处理中...'

        const requestData = {
          task_id: taskId,
          config: {
            confidence: detectConfig.confidence,
            input_size: detectConfig.inputSize,
            device: detectConfig.device,
            output_format: detectConfig.outputFormat,
            alert_behaviors: detectConfig.alertBehaviors,
            save_results: detectConfig.saveResults
          }
        }

        console.log('🚀 开始检测请求:', requestData)

        const response = await fetch('http://localhost:5000/api/detect/video', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestData)
        })

        console.log('📡 检测响应状态:', response.status)

        if (response.ok) {
          const result = await response.json()
          console.log('✅ 检测响应数据:', result)

          uploadProgress.value = 100
          uploadStatus.value = 'success'
          uploadStatusText.value = '检测完成'

          ElMessage.success('视频检测完成')

          // 重置状态
          setTimeout(() => {
            uploading.value = false
            removeFile()
            refreshHistory()
          }, 2000)

        } else {
          const errorData = await response.json()
          console.error('❌ 检测失败响应:', errorData)
          throw new Error(errorData.error || '检测失败')
        }
      } catch (error) {
        console.error('❌ 检测错误:', error)
        ElMessage.error('检测失败: ' + error.message)
        uploading.value = false
        uploadStatus.value = 'exception'
        uploadStatusText.value = '检测失败'
      }
    }

    // 刷新历史记录
    const refreshHistory = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/tasks?type=video')
        if (response.ok) {
          const data = await response.json()
          uploadHistory.value = data.tasks || []
        }
      } catch (error) {
        console.error('获取历史记录失败:', error)
      }
    }

    // 查看结果
    const viewResults = async (record) => {
      try {
        const response = await fetch(`http://localhost:5000/api/tasks/${record.id}/results`)
        if (response.ok) {
          const data = await response.json()
          currentResult.value = data
          showResultDialog.value = true
        } else {
          ElMessage.error('获取结果失败')
        }
      } catch (error) {
        ElMessage.error('获取结果失败')
        console.error('获取结果错误:', error)
      }
    }

    // 删除记录
    const deleteRecord = async (record) => {
      try {
        await ElMessageBox.confirm('确定要删除这条记录吗？', '确认删除', {
          type: 'warning'
        })
        
        const response = await fetch(`http://localhost:5000/api/tasks/${record.id}`, {
          method: 'DELETE'
        })
        
        if (response.ok) {
          ElMessage.success('删除成功')
          refreshHistory()
        } else {
          ElMessage.error('删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    // 下载结果
    const downloadResults = () => {
      if (currentResult.value) {
        const link = document.createElement('a')
        link.href = currentResult.value.downloadUrl
        link.download = `results_${currentResult.value.filename}`
        link.click()
      }
    }

    // 关闭结果对话框
    const handleResultDialogClose = () => {
      showResultDialog.value = false
      currentResult.value = null
    }

    // 工具函数
    const formatFileSize = (bytes) => {
      // 处理空值、undefined 或无效数据
      if (!bytes || bytes === null || bytes === undefined || isNaN(bytes)) {
        return '--'
      }
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const getFileExtension = (filename) => {
      if (!filename || typeof filename !== 'string') {
        return '--'
      }
      return filename.split('.').pop().toUpperCase()
    }

    const formatDateTime = (timestamp) => {
      // 处理空值、undefined 或无效时间戳
      if (!timestamp || timestamp === null || timestamp === undefined) {
        return '--'
      }
      
      const date = new Date(timestamp)
      // 检查日期是否有效
      if (isNaN(date.getTime())) {
        return '--'
      }
      
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    const getStatusType = (status) => {
      const typeMap = {
        'pending': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger'
      }
      return typeMap[status] || 'info'
    }

    const getStatusText = (status) => {
      const textMap = {
        'pending': '等待中',
        'processing': '处理中',
        'completed': '已完成',
        'failed': '失败'
      }
      return textMap[status] || '未知'
    }

    onMounted(() => {
      refreshHistory()
    })

    return {
      uploadRef,
      selectedFile,
      uploading,
      uploadProgress,
      uploadStatus,
      uploadStatusText,
      uploadHistory,
      showResultDialog,
      currentResult,
      detectConfig,
      handleFileChange,
      handleFileRemove,
      removeFile,
      startUpload,
      refreshHistory,
      viewResults,
      deleteRecord,
      downloadResults,
      handleResultDialogClose,
      formatFileSize,
      getFileExtension,
      formatDateTime,
      getStatusType,
      getStatusText
    }
  }
}
</script>

<style scoped>
.video-upload {
  padding: 0;
}

.upload-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-area {
  padding: 20px 0;
}

.upload-dragger {
  width: 100%;
}

.upload-content {
  padding: 40px 20px;
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  color: #606266;
  font-size: 14px;
}

.upload-text p {
  margin: 8px 0;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-hint {
  color: #909399;
  font-size: 12px;
}

.file-info {
  margin-top: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.file-details {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.file-icon {
  color: #409eff;
}

.file-content {
  flex: 1;
}

.file-name {
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.file-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 16px;
}

.upload-progress {
  margin-top: 12px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
}

.config-card {
  margin-bottom: 20px;
}

.config-form {
  padding: 0 20px;
}

.history-card {
  margin-bottom: 20px;
}

.filename-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-history {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.empty-history p {
  margin: 16px 0 0 0;
}

.result-content {
  padding: 20px 0;
}

.result-video {
  margin-bottom: 24px;
  text-align: center;
}

.result-stats {
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.behavior-analysis h4 {
  margin: 0 0 16px 0;
  color: #303133;
}
</style> 