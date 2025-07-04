/**
 * 统一配置管理工具
 * 用于管理实时监控和视频上传的配置
 */

// 默认配置定义
export const DEFAULT_CONFIG = {
  // 基础检测配置
  confidence: 0.5,
  inputSize: 640,
  device: 'auto',
  
  // 报警行为配置
  alertBehaviors: ['fall down', 'fight', 'enter', 'exit'],
  
  // 高级配置（主要用于视频上传）
  outputFormat: 'video',
  saveResults: true,
  
  // 实时监控特有配置
  recording: false,
  alertEnabled: true,
  
  // 性能配置
  maxConcurrentTasks: 3,
  autoCleanup: true,
  cleanupDays: 30
}

// 所有可用的报警行为
export const AVAILABLE_BEHAVIORS = [
  { label: 'fall down', name: '跌倒' },
  { label: 'fight', name: '打斗' },
  { label: 'enter', name: '闯入' },
  { label: 'exit', name: '离开' },
  { label: 'run', name: '奔跑' },
  { label: 'sit', name: '坐下' },
  { label: 'stand', name: '站立' },
  { label: 'walk', name: '行走' }
]

// 设备选项
export const DEVICE_OPTIONS = [
  { label: 'auto', name: '自动选择' },
  { label: 'cpu', name: 'CPU' },
  { label: 'cuda', name: 'GPU' }
]

// 输入尺寸选项（已废弃，使用固定值640）
export const INPUT_SIZE_OPTIONS = [
  { value: 640, label: '640x640 (默认)' }
]

// 输出格式选项（已废弃，使用固定值video）
export const OUTPUT_FORMAT_OPTIONS = [
  { value: 'video', label: '视频文件 (默认)' }
]

/**
 * 配置管理类
 */
export class ConfigManager {
  constructor() {
    this.storageKey = 'behavior_detection_config'
  }

  /**
   * 获取完整配置
   * @param {string} mode - 配置模式 ('realtime' | 'upload')
   * @returns {Object} 配置对象
   */
  getConfig(mode = 'realtime') {
    const savedConfig = this.loadFromStorage()
    const config = { ...DEFAULT_CONFIG, ...savedConfig }
    
    if (mode === 'realtime') {
      // 实时监控模式：返回简化配置（不包含输入尺寸和高级选项）
      return {
        confidence: config.confidence,
        alertBehaviors: config.alertBehaviors, // 返回所有8个报警行为
        device: config.device,
        alertEnabled: config.alertEnabled
      }
    } else if (mode === 'upload') {
      // 上传模式：返回完整配置
      return config
    }
    
    return config
  }

  /**
   * 保存配置
   * @param {Object} config - 配置对象
   * @param {string} mode - 配置模式
   */
  saveConfig(config, mode = 'realtime') {
    const currentConfig = this.loadFromStorage()
    let updatedConfig = { ...currentConfig }

    if (mode === 'realtime') {
      // 实时监控模式：只更新相关配置
      updatedConfig = {
        ...updatedConfig,
        confidence: config.confidence,
        alertBehaviors: config.alertBehaviors,
        device: config.device || 'auto',
        inputSize: config.inputSize || 640,
        recording: config.recording,
        alertEnabled: config.alertEnabled
      }
    } else if (mode === 'upload') {
      // 上传模式：更新完整配置
      updatedConfig = { ...updatedConfig, ...config }
    }

    this.saveToStorage(updatedConfig)
    return updatedConfig
  }

  /**
   * 从localStorage加载配置
   */
  loadFromStorage() {
    try {
      const saved = localStorage.getItem(this.storageKey)
      return saved ? JSON.parse(saved) : {}
    } catch (error) {
      console.warn('加载配置失败:', error)
      return {}
    }
  }

  /**
   * 保存配置到localStorage
   */
  saveToStorage(config) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(config))
    } catch (error) {
      console.warn('保存配置失败:', error)
    }
  }

  /**
   * 重置配置为默认值
   */
  resetConfig() {
    localStorage.removeItem(this.storageKey)
    return { ...DEFAULT_CONFIG }
  }

  /**
   * 验证配置
   * @param {Object} config - 配置对象
   * @returns {Object} 验证结果
   */
  validateConfig(config) {
    const errors = []

    // 验证置信度
    if (config.confidence < 0.1 || config.confidence > 1.0) {
      errors.push('检测置信度必须在0.1-1.0之间')
    }

    // 验证输入尺寸（仅当配置中包含inputSize时）
    if (config.hasOwnProperty('inputSize')) {
      const validSizes = INPUT_SIZE_OPTIONS.map(opt => opt.value)
      if (!validSizes.includes(config.inputSize)) {
        errors.push('输入尺寸无效')
      }
    }

    // 验证设备类型
    const validDevices = DEVICE_OPTIONS.map(opt => opt.label)
    if (!validDevices.includes(config.device)) {
      errors.push('设备类型无效')
    }

    // 验证报警行为
    if (!Array.isArray(config.alertBehaviors) || config.alertBehaviors.length === 0) {
      errors.push('至少需要选择一个报警行为')
    }

    return {
      isValid: errors.length === 0,
      errors
    }
  }

  /**
   * 转换配置为后端格式
   * @param {Object} config - 前端配置
   * @param {string} mode - 模式
   * @returns {Object} 后端配置格式
   */
  toBackendFormat(config, mode = 'realtime') {
    const backendConfig = {
      confidence_threshold: config.confidence,
      device: config.device,
      alert_behaviors: config.alertBehaviors
    }

    if (mode === 'realtime') {
      // 实时监控使用默认输入尺寸
      backendConfig.input_size = 640
    } else if (mode === 'upload') {
      // 上传模式使用完整配置
      backendConfig.input_size = config.inputSize
      backendConfig.output_format = config.outputFormat
      backendConfig.save_results = config.saveResults
    }

    return backendConfig
  }

  /**
   * 获取配置差异
   * @param {Object} config1 - 配置1
   * @param {Object} config2 - 配置2
   * @returns {Object} 差异对象
   */
  getConfigDiff(config1, config2) {
    const diff = {}
    const allKeys = new Set([...Object.keys(config1), ...Object.keys(config2)])
    
    for (const key of allKeys) {
      if (JSON.stringify(config1[key]) !== JSON.stringify(config2[key])) {
        diff[key] = {
          old: config1[key],
          new: config2[key]
        }
      }
    }
    
    return diff
  }
}

// 导出单例实例
export const configManager = new ConfigManager()

// 导出便捷函数
export const getRealtimeConfig = () => configManager.getConfig('realtime')
export const getUploadConfig = () => configManager.getConfig('upload')
export const saveRealtimeConfig = (config) => configManager.saveConfig(config, 'realtime')
export const saveUploadConfig = (config) => configManager.saveConfig(config, 'upload')
