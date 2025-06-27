import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import store from './store'

// Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// 样式文件
import './styles/main.scss'

// 进度条
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 配置NProgress
NProgress.configure({ 
  showSpinner: false,
  minimum: 0.2,
  speed: 500
})

// API配置
const API_BASE_URL = 'http://localhost:5000'

// 导入页面组件
import Dashboard from './views/Dashboard.vue'
import VideoUpload from './views/VideoUpload.vue'
import RealtimeMonitor from './views/RealtimeMonitor.vue'
import TaskManager from './views/TaskManager.vue'
import AlertRecords from './views/AlertRecords.vue'
import Statistics from './views/Statistics.vue'
import Settings from './views/Settings.vue'

// 路由配置
const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/upload',
    name: 'VideoUpload',
    component: VideoUpload
  },
  {
    path: '/realtime',
    name: 'RealtimeMonitor',
    component: RealtimeMonitor
  },
  {
    path: '/tasks',
    name: 'TaskManager',
    component: TaskManager
  },
  {
    path: '/alerts',
    name: 'AlertRecords',
    component: AlertRecords
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: Statistics
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 创建Vue应用
const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 使用插件
app.use(store)
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

// 全局属性
app.config.globalProperties.$ELEMENT = { size: 'default' }
app.config.globalProperties.$API_BASE_URL = API_BASE_URL

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('全局错误:', err)
  console.error('错误信息:', info)
}

// 挂载应用
app.mount('#app') 