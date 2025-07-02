// API配置和工具函数
const API_BASE_URL = 'http://localhost:5001'

// 创建API请求函数
export const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  }
  
  const finalOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  }
  
  // 如果body是对象，自动序列化
  if (finalOptions.body && typeof finalOptions.body === 'object' && !(finalOptions.body instanceof FormData)) {
    finalOptions.body = JSON.stringify(finalOptions.body);
  }
  
  try {
    const response = await fetch(url, finalOptions)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error(`API请求失败: ${endpoint}`, error)
    throw error
  }
}

// 健康检查
export const checkHealth = () => apiRequest('/api/health')

// 获取报警记录
export const getAlerts = (params = {}) => {
  const queryString = new URLSearchParams(params).toString()
  return apiRequest(`/api/alerts${queryString ? '?' + queryString : ''}`)
}

// 获取任务列表
export const getTasks = (params = {}) => {
  const queryString = new URLSearchParams(params).toString()
  return apiRequest(`/api/tasks${queryString ? '?' + queryString : ''}`)
}

// 获取任务详情
export const getTask = (taskId) => apiRequest(`/api/tasks/${taskId}`)

// 获取任务结果
export const getTaskResults = (taskId) => apiRequest(`/api/tasks/${taskId}/results`)

// 启动视频检测
export const startVideoDetection = (data) => apiRequest('/api/detect/video', {
  method: 'POST',
  body: JSON.stringify(data)
})

// 启动实时检测
export const startRealtimeDetection = (data) => apiRequest('/api/detect/realtime', {
  method: 'POST',
  body: JSON.stringify(data)
})

// 停止检测
export const stopDetection = (taskId) => apiRequest(`/api/detect/stop/${taskId}`, {
  method: 'POST'
})

// 获取统计数据
export const getStatistics = (params = {}) => {
  const queryString = new URLSearchParams(params).toString()
  return apiRequest(`/api/statistics${queryString ? '?' + queryString : ''}`)
}

// 获取系统信息
export const getSystemInfo = () => apiRequest('/api/system/info')

// 获取系统设置
export const getSettings = () => apiRequest('/api/settings')

// 更新系统设置
export const updateSettings = (settings) => apiRequest('/api/settings', {
  method: 'POST',
  body: JSON.stringify(settings)
})

// 批量删除任务
export const batchDeleteTasks = (taskIds) => apiRequest('/api/tasks/batch-delete', {
  method: 'POST',
  body: JSON.stringify({ task_ids: taskIds })
})

// 下载结果文件
export const downloadResult = (taskId) => `${API_BASE_URL}/api/download/result/${taskId}`

export { API_BASE_URL } 