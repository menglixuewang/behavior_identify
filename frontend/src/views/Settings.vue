<template>
  <div class="settings">
    <el-tabs v-model="activeTab" type="card" class="settings-tabs">
      <!-- 检测配置 -->
      <el-tab-pane label="检测配置" name="detection">
        <el-card>
          <template #header>
            <span>检测参数设置</span>
          </template>
          
          <el-form :model="detectionSettings" label-width="150px" class="settings-form">
            <el-form-item label="默认置信度阈值">
              <el-slider
                v-model="detectionSettings.confidence"
                :min="0.1"
                :max="1.0"
                :step="0.05"
                show-stops
                show-input
                :input-size="'small'"
              />
              <div class="form-tip">设置检测结果的最低置信度要求</div>
            </el-form-item>
            
            <el-form-item label="默认输入尺寸">
              <el-select v-model="detectionSettings.inputSize" placeholder="选择输入尺寸">
                <el-option label="416x416 (快速)" :value="416" />
                <el-option label="640x640 (平衡)" :value="640" />
                <el-option label="832x832 (精确)" :value="832" />
              </el-select>
              <div class="form-tip">更大的输入尺寸可提高检测精度但会降低速度</div>
            </el-form-item>
            
            <el-form-item label="默认设备类型">
              <el-radio-group v-model="detectionSettings.device">
                <el-radio label="cpu">CPU (兼容性好)</el-radio>
                <el-radio label="cuda">GPU (性能更快)</el-radio>
              </el-radio-group>
              <div class="form-tip">GPU需要CUDA支持，CPU适合所有环境</div>
            </el-form-item>
            
            <el-form-item label="并发任务数限制">
              <el-input-number 
                v-model="detectionSettings.maxConcurrentTasks" 
                :min="1" 
                :max="10"
                controls-position="right"
              />
              <div class="form-tip">同时运行的检测任务数量上限</div>
            </el-form-item>
            
            <el-form-item label="自动清理结果">
              <el-switch
                v-model="detectionSettings.autoCleanup"
                active-text="启用"
                inactive-text="禁用"
              />
              <el-input-number 
                v-if="detectionSettings.autoCleanup"
                v-model="detectionSettings.cleanupDays" 
                :min="1" 
                :max="365"
                controls-position="right"
                style="margin-left: 12px;"
              />
              <span v-if="detectionSettings.autoCleanup" style="margin-left: 8px;">天后自动删除</span>
              <div class="form-tip">自动清理过期的检测结果和文件</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 报警配置 -->
      <el-tab-pane label="报警配置" name="alert">
        <el-card>
          <template #header>
            <span>报警规则设置</span>
          </template>
          
          <el-form :model="alertSettings" label-width="150px" class="settings-form">
            <el-form-item label="启用报警">
              <el-switch
                v-model="alertSettings.enabled"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="form-tip">是否启用智能报警功能</div>
            </el-form-item>
            
            <el-form-item label="报警行为类型" v-if="alertSettings.enabled">
              <el-checkbox-group v-model="alertSettings.behaviors">
                <el-checkbox label="fall down">跌倒</el-checkbox>
                <el-checkbox label="fight">打斗</el-checkbox>
                <el-checkbox label="enter">闯入</el-checkbox>
                <el-checkbox label="exit">离开</el-checkbox>
                <el-checkbox label="run">奔跑</el-checkbox>
                <el-checkbox label="sit">坐下</el-checkbox>
                <el-checkbox label="stand">站立</el-checkbox>
                <el-checkbox label="walk">行走</el-checkbox>
              </el-checkbox-group>
              <div class="form-tip">选择需要触发报警的行为类型</div>
            </el-form-item>
            
            <el-form-item label="报警置信度阈值" v-if="alertSettings.enabled">
              <el-slider
                v-model="alertSettings.confidenceThreshold"
                :min="0.1"
                :max="1.0"
                :step="0.05"
                show-stops
                show-input
                :input-size="'small'"
              />
              <div class="form-tip">只有置信度超过此阈值才会触发报警</div>
            </el-form-item>
            
            <el-form-item label="报警冷却时间" v-if="alertSettings.enabled">
              <el-input-number 
                v-model="alertSettings.cooldownSeconds" 
                :min="1" 
                :max="300"
                controls-position="right"
              />
              <span style="margin-left: 8px;">秒</span>
              <div class="form-tip">同一类型报警的最小间隔时间</div>
            </el-form-item>
            
            <el-form-item label="声音提醒" v-if="alertSettings.enabled">
              <el-switch
                v-model="alertSettings.soundEnabled"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="form-tip">报警时播放提示音</div>
            </el-form-item>
            
            <el-form-item label="邮件通知" v-if="alertSettings.enabled">
              <el-switch
                v-model="alertSettings.emailEnabled"
                active-text="启用"
                inactive-text="禁用"
              />
              <el-input 
                v-if="alertSettings.emailEnabled"
                v-model="alertSettings.emailAddress" 
                placeholder="输入邮箱地址"
                style="margin-top: 8px;"
              />
              <div class="form-tip">重要报警时发送邮件通知</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 存储配置 -->
      <el-tab-pane label="存储配置" name="storage">
        <el-card>
          <template #header>
            <span>文件存储设置</span>
          </template>
          
          <el-form :model="storageSettings" label-width="150px" class="settings-form">
            <el-form-item label="上传文件大小限制">
              <el-input-number 
                v-model="storageSettings.maxFileSize" 
                :min="10" 
                :max="2048"
                controls-position="right"
              />
              <span style="margin-left: 8px;">MB</span>
              <div class="form-tip">单个上传文件的最大大小</div>
            </el-form-item>
            
            <el-form-item label="支持的文件格式">
              <el-checkbox-group v-model="storageSettings.allowedFormats">
                <el-checkbox label="mp4">MP4</el-checkbox>
                <el-checkbox label="avi">AVI</el-checkbox>
                <el-checkbox label="mov">MOV</el-checkbox>
                <el-checkbox label="mkv">MKV</el-checkbox>
                <el-checkbox label="flv">FLV</el-checkbox>
                <el-checkbox label="wmv">WMV</el-checkbox>
              </el-checkbox-group>
              <div class="form-tip">允许上传的视频文件格式</div>
            </el-form-item>
            
            <el-form-item label="存储路径">
              <el-input 
                v-model="storageSettings.storagePath" 
                placeholder="输入存储路径"
                readonly
              />
              <el-button type="primary" size="small" @click="selectStoragePath" style="margin-left: 8px;">
                选择路径
              </el-button>
              <div class="form-tip">文件和结果的存储目录</div>
            </el-form-item>
            
            <el-form-item label="自动备份">
              <el-switch
                v-model="storageSettings.autoBackup"
                active-text="启用"
                inactive-text="禁用"
              />
              <el-select 
                v-if="storageSettings.autoBackup"
                v-model="storageSettings.backupInterval" 
                style="margin-left: 12px;"
              >
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
              <div class="form-tip">定期备份重要数据</div>
            </el-form-item>
            
            <el-form-item label="磁盘空间监控">
              <el-switch
                v-model="storageSettings.diskMonitoring"
                active-text="启用"
                inactive-text="禁用"
              />
              <el-input-number 
                v-if="storageSettings.diskMonitoring"
                v-model="storageSettings.diskWarningThreshold" 
                :min="10" 
                :max="95"
                controls-position="right"
                style="margin-left: 12px;"
              />
              <span v-if="storageSettings.diskMonitoring" style="margin-left: 8px;">% 时警告</span>
              <div class="form-tip">磁盘使用率超过阈值时发出警告</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 系统配置 -->
      <el-tab-pane label="系统配置" name="system">
        <el-card>
          <template #header>
            <span>系统运行设置</span>
          </template>
          
          <el-form :model="systemSettings" label-width="150px" class="settings-form">
            <el-form-item label="系统语言">
              <el-select v-model="systemSettings.language">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
              </el-select>
              <div class="form-tip">系统界面显示语言</div>
            </el-form-item>
            
            <el-form-item label="日志级别">
              <el-select v-model="systemSettings.logLevel">
                <el-option label="调试 (DEBUG)" value="debug" />
                <el-option label="信息 (INFO)" value="info" />
                <el-option label="警告 (WARNING)" value="warning" />
                <el-option label="错误 (ERROR)" value="error" />
              </el-select>
              <div class="form-tip">系统日志记录的详细程度</div>
            </el-form-item>
            
            <el-form-item label="日志保留天数">
              <el-input-number 
                v-model="systemSettings.logRetentionDays" 
                :min="1" 
                :max="365"
                controls-position="right"
              />
              <span style="margin-left: 8px;">天</span>
              <div class="form-tip">系统日志文件的保留时间</div>
            </el-form-item>
            
            <el-form-item label="性能监控">
              <el-switch
                v-model="systemSettings.performanceMonitoring"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="form-tip">监控系统CPU、内存、GPU使用情况</div>
            </el-form-item>
            
            <el-form-item label="自动更新检查">
              <el-switch
                v-model="systemSettings.autoUpdateCheck"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="form-tip">自动检查系统更新</div>
            </el-form-item>
            
            <el-form-item label="API访问限制">
              <el-switch
                v-model="systemSettings.apiRateLimit"
                active-text="启用"
                inactive-text="禁用"
              />
              <el-input-number 
                v-if="systemSettings.apiRateLimit"
                v-model="systemSettings.apiRatePerMinute" 
                :min="10" 
                :max="1000"
                controls-position="right"
                style="margin-left: 12px;"
              />
              <span v-if="systemSettings.apiRateLimit" style="margin-left: 8px;">次/分钟</span>
              <div class="form-tip">限制API调用频率，防止滥用</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 关于系统 -->
      <el-tab-pane label="关于系统" name="about">
        <el-card>
          <template #header>
            <span>系统信息</span>
          </template>
          
          <div class="about-content">
            <div class="system-info">
              <h3>智能行为检测系统</h3>
              <p class="version">版本: v1.0.0</p>
              <p class="description">
                基于YOLOv8+SlowFast的智能行为检测系统，支持实时监控和视频分析，
                可识别多种人体行为并进行智能报警。
              </p>
            </div>
            
            <el-descriptions title="技术栈信息" :column="2" border>
              <el-descriptions-item label="前端框架">Vue 3 + Element Plus</el-descriptions-item>
              <el-descriptions-item label="后端框架">Flask + SQLite</el-descriptions-item>
              <el-descriptions-item label="检测算法">YOLOv8 + SlowFast</el-descriptions-item>
              <el-descriptions-item label="深度学习">PyTorch</el-descriptions-item>
              <el-descriptions-item label="目标跟踪">DeepSort</el-descriptions-item>
              <el-descriptions-item label="开发语言">Python + JavaScript</el-descriptions-item>
            </el-descriptions>
            
            <el-descriptions title="系统状态" :column="2" border style="margin-top: 20px;">
              <el-descriptions-item label="运行时间">{{ systemInfo.uptime }}</el-descriptions-item>
              <el-descriptions-item label="CPU使用率">{{ systemInfo.cpuUsage }}%</el-descriptions-item>
              <el-descriptions-item label="内存使用率">{{ systemInfo.memoryUsage }}%</el-descriptions-item>
              <el-descriptions-item label="磁盘使用率">{{ systemInfo.diskUsage }}%</el-descriptions-item>
              <el-descriptions-item label="Python版本">{{ systemInfo.pythonVersion }}</el-descriptions-item>
              <el-descriptions-item label="PyTorch版本">{{ systemInfo.torchVersion }}</el-descriptions-item>
            </el-descriptions>
            
            <div class="action-buttons">
              <el-button type="primary" @click="checkUpdates">检查更新</el-button>
              <el-button type="success" @click="exportLogs">导出日志</el-button>
              <el-button type="warning" @click="restartSystem">重启系统</el-button>
              <el-button type="danger" @click="resetSettings">重置设置</el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 保存按钮 -->
    <div class="save-actions">
      <el-button @click="resetCurrentTab">重置</el-button>
      <el-button type="primary" @click="saveSettings">保存设置</el-button>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Settings',
  setup() {
    const activeTab = ref('detection')
    
    // 检测配置
    const detectionSettings = reactive({
      confidence: 0.5,
      inputSize: 640,
      device: 'cpu',
      maxConcurrentTasks: 3,
      autoCleanup: true,
      cleanupDays: 30
    })
    
    // 报警配置
    const alertSettings = reactive({
      enabled: true,
      behaviors: ['fall down', 'fight', 'enter', 'exit'],
      confidenceThreshold: 0.7,
      cooldownSeconds: 30,
      soundEnabled: true,
      emailEnabled: false,
      emailAddress: ''
    })
    
    // 存储配置
    const storageSettings = reactive({
      maxFileSize: 500,
      allowedFormats: ['mp4', 'avi', 'mov', 'mkv'],
      storagePath: '/data/behavior_detection',
      autoBackup: false,
      backupInterval: 'weekly',
      diskMonitoring: true,
      diskWarningThreshold: 85
    })
    
    // 系统配置
    const systemSettings = reactive({
      language: 'zh-CN',
      logLevel: 'info',
      logRetentionDays: 30,
      performanceMonitoring: true,
      autoUpdateCheck: true,
      apiRateLimit: false,
      apiRatePerMinute: 100
    })
    
    // 系统信息
    const systemInfo = reactive({
      uptime: '0天0小时',
      cpuUsage: 0,
      memoryUsage: 0,
      diskUsage: 0,
      pythonVersion: '',
      torchVersion: ''
    })

    // 加载设置
    const loadSettings = async () => {
      try {
        const response = await fetch('/api/settings')
        if (response.ok) {
          const data = await response.json()
          
          if (data.detection) Object.assign(detectionSettings, data.detection)
          if (data.alert) Object.assign(alertSettings, data.alert)
          if (data.storage) Object.assign(storageSettings, data.storage)
          if (data.system) Object.assign(systemSettings, data.system)
        }
      } catch (error) {
        console.error('加载设置失败:', error)
      }
    }

    // 加载系统信息
    const loadSystemInfo = async () => {
      try {
        const response = await fetch('/api/system/info')
        if (response.ok) {
          const data = await response.json()
          Object.assign(systemInfo, data)
        }
      } catch (error) {
        console.error('加载系统信息失败:', error)
      }
    }

    // 保存设置
    const saveSettings = async () => {
      try {
        const settings = {
          detection: detectionSettings,
          alert: alertSettings,
          storage: storageSettings,
          system: systemSettings
        }
        
        const response = await fetch('/api/settings', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(settings)
        })
        
        if (response.ok) {
          ElMessage.success('设置保存成功')
        } else {
          ElMessage.error('设置保存失败')
        }
      } catch (error) {
        ElMessage.error('设置保存失败')
        console.error('保存设置错误:', error)
      }
    }

    // 重置当前标签页设置
    const resetCurrentTab = () => {
      ElMessageBox.confirm('确定要重置当前页面的设置吗？', '确认重置', {
        type: 'warning'
      }).then(() => {
        // 重新加载设置
        loadSettings()
        ElMessage.success('设置已重置')
      }).catch(() => {})
    }

    // 选择存储路径
    const selectStoragePath = () => {
      ElMessage.info('请在系统文件管理器中选择存储路径')
      // 这里可以集成文件选择器
    }

    // 检查更新
    const checkUpdates = async () => {
      try {
        const response = await fetch('/api/system/check-updates')
        if (response.ok) {
          const data = await response.json()
          if (data.hasUpdate) {
            ElMessageBox.confirm(`发现新版本 ${data.latestVersion}，是否立即更新？`, '发现更新', {
              type: 'info'
            }).then(() => {
              ElMessage.info('开始下载更新...')
            }).catch(() => {})
          } else {
            ElMessage.success('当前已是最新版本')
          }
        }
      } catch (error) {
        ElMessage.error('检查更新失败')
      }
    }

    // 导出日志
    const exportLogs = async () => {
      try {
        const response = await fetch('/api/system/export-logs')
        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = `system_logs_${new Date().toISOString().split('T')[0]}.zip`
          link.click()
          window.URL.revokeObjectURL(url)
          
          ElMessage.success('日志导出成功')
        }
      } catch (error) {
        ElMessage.error('日志导出失败')
      }
    }

    // 重启系统
    const restartSystem = () => {
      ElMessageBox.confirm('确定要重启系统吗？这将中断所有正在运行的任务。', '确认重启', {
        type: 'warning'
      }).then(async () => {
        try {
          await fetch('/api/system/restart', { method: 'POST' })
          ElMessage.success('系统正在重启...')
        } catch (error) {
          ElMessage.error('重启失败')
        }
      }).catch(() => {})
    }

    // 重置所有设置
    const resetSettings = () => {
      ElMessageBox.confirm('确定要重置所有设置为默认值吗？此操作不可恢复。', '确认重置', {
        type: 'warning'
      }).then(async () => {
        try {
          const response = await fetch('/api/settings/reset', { method: 'POST' })
          if (response.ok) {
            loadSettings()
            ElMessage.success('设置已重置为默认值')
          }
        } catch (error) {
          ElMessage.error('重置失败')
        }
      }).catch(() => {})
    }

    onMounted(() => {
      loadSettings()
      loadSystemInfo()
      
      // 定期更新系统信息
      setInterval(loadSystemInfo, 30000)
    })

    return {
      activeTab,
      detectionSettings,
      alertSettings,
      storageSettings,
      systemSettings,
      systemInfo,
      saveSettings,
      resetCurrentTab,
      selectStoragePath,
      checkUpdates,
      exportLogs,
      restartSystem,
      resetSettings
    }
  }
}
</script>

<style scoped>
.settings {
  padding: 0;
}

.settings-tabs {
  margin-bottom: 20px;
}

.settings-form {
  max-width: 800px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

.about-content {
  max-width: 800px;
}

.system-info {
  text-align: center;
  margin-bottom: 30px;
}

.system-info h3 {
  color: #303133;
  margin-bottom: 8px;
}

.version {
  color: #409eff;
  font-weight: bold;
  margin-bottom: 16px;
}

.description {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 0;
}

.action-buttons {
  margin-top: 30px;
  text-align: center;
}

.action-buttons .el-button {
  margin: 0 8px;
}

.save-actions {
  text-align: right;
  padding: 20px 0;
  border-top: 1px solid #e4e7ed;
}

.save-actions .el-button {
  margin-left: 12px;
}

:deep(.el-tabs__content) {
  padding: 0;
}

:deep(.el-card) {
  border: none;
  box-shadow: none;
}

:deep(.el-card__header) {
  padding: 18px 20px;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.el-card__body) {
  padding: 20px;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-slider) {
  margin-left: 12px;
  margin-right: 12px;
}

:deep(.el-checkbox-group) {
  line-height: 1.8;
}

:deep(.el-checkbox) {
  margin-right: 20px;
  margin-bottom: 8px;
}
</style> 