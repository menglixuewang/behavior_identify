import { createStore } from 'vuex'

export default createStore({
  state: {
    // 用户信息
    user: {
      name: 'Admin',
      role: 'administrator'
    },
    // 系统状态
    system: {
      status: 'running',
      version: '1.0.0'
    },
    // 检测任务
    tasks: [],
    // 报警记录
    alerts: [],
    // 统计数据
    statistics: {
      totalTasks: 0,
      totalAlerts: 0,
      todayTasks: 0,
      todayAlerts: 0
    }
  },
  mutations: {
    // 设置用户信息
    SET_USER(state, user) {
      state.user = user
    },
    // 设置系统状态
    SET_SYSTEM_STATUS(state, status) {
      state.system.status = status
    },
    // 添加任务
    ADD_TASK(state, task) {
      state.tasks.push(task)
    },
    // 更新任务状态
    UPDATE_TASK(state, { id, status }) {
      const task = state.tasks.find(t => t.id === id)
      if (task) {
        task.status = status
      }
    },
    // 添加报警
    ADD_ALERT(state, alert) {
      state.alerts.push(alert)
    },
    // 更新统计数据
    UPDATE_STATISTICS(state, stats) {
      state.statistics = { ...state.statistics, ...stats }
    }
  },
  actions: {
    // 获取系统状态
    async fetchSystemStatus({ commit }) {
      try {
        // 这里可以调用实际的API
        const response = await fetch('/api/health')
        const data = await response.json()
        commit('SET_SYSTEM_STATUS', data.status)
        return data
      } catch (error) {
        console.error('获取系统状态失败:', error)
        throw error
      }
    },
    // 获取统计数据
    async fetchStatistics({ commit }) {
      try {
        // 模拟API调用
        const stats = {
          totalTasks: 156,
          totalAlerts: 23,
          todayTasks: 12,
          todayAlerts: 3
        }
        commit('UPDATE_STATISTICS', stats)
        return stats
      } catch (error) {
        console.error('获取统计数据失败:', error)
        throw error
      }
    }
  },
  getters: {
    // 获取未处理的报警数量
    pendingAlertsCount: state => {
      return state.alerts.filter(alert => alert.status === 'pending').length
    },
    // 获取今日任务数量
    todayTasksCount: state => {
      return state.statistics.todayTasks
    },
    // 获取系统运行状态
    isSystemRunning: state => {
      return state.system.status === 'running'
    }
  }
}) 