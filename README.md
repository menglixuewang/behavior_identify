# 🎯 智能行为检测系统

基于YOLOv8+SlowFast算法的智能行为检测系统，支持视频上传检测、实时监控、结果展示和数据统计等功能。

![系统架构](https://img.shields.io/badge/架构-前后端分离-blue)
![Python版本](https://img.shields.io/badge/Python-3.8+-green)
![Vue版本](https://img.shields.io/badge/Vue.js-3.3+-brightgreen)
![许可证](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 功能特性

- 🎥 **视频文件检测** - 支持多种格式视频上传和批量处理
- 📹 **实时监控** - 多路摄像头同时监控，实时行为识别  
- 🚨 **智能报警** - 自动识别异常行为并及时报警
- 📊 **数据分析** - 丰富的统计图表和可视化展示
- 💻 **Web界面** - 美观易用的管理界面
- 🎯 **目标跟踪** - DeepSort算法实现精准目标跟踪
- 🔔 **实时通信** - WebSocket实现实时数据推送

## 🧠 检测能力

系统可以识别多种人体行为，包括但不限于：

| 行为类别 | 描述 | 报警级别 |
|---------|------|---------|
| 🚶‍♂️ 正常行走 | 常规的人员移动 | - |
| 🏃‍♂️ 奔跑 | 快速移动行为 | 低 |
| 🤸‍♂️ 跌倒 | 人员摔倒检测 | **高** |
| 👊 打斗 | 暴力行为识别 | **高** |
| 🚪 进入/离开 | 区域闯入检测 | 中 |
| 🔄 徘徊 | 可疑徘徊行为 | 中 |

## 项目结构

```
behavior_detection_system/
├── yolo_slowfast-master/     # 核心算法模块
├── backend/                  # 后端API服务
│   ├── app.py               # Flask主应用
│   ├── models/              # 数据模型
│   ├── apis/                # API接口
│   ├── services/            # 业务逻辑
│   └── utils/               # 工具函数
├── frontend/                # Vue.js前端
│   ├── src/                 # 源代码
│   ├── public/              # 静态资源
│   └── dist/                # 构建输出
├── database/                # 数据库相关
├── uploads/                 # 上传文件目录
├── outputs/                 # 输出文件目录
├── logs/                    # 日志文件
└── config/                  # 配置文件
```

## 技术栈

- **后端**: Flask + SQLite
- **前端**: Vue.js + Element UI
- **算法**: YOLOv8 + SlowFast
- **数据库**: SQLite
- **实时通信**: WebSocket

## 功能特性

- 🎥 视频文件上传检测
- 📹 实时摄像头监控
- 🎯 多种行为识别（跌倒、徘徊、闯入等）
- 📊 检测结果统计分析
- 🚨 异常行为报警
- 📱 响应式Web界面

## 快速开始

### 环境依赖

- Python 3.8+
- Node.js 14+
- npm/yarn

### 安装步骤

1. 克隆项目
```bash
git clone [repository-url]
cd behavior_detection_system
```

2. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

3. 安装前端依赖
```bash
cd frontend
npm install
```

4. 启动服务
```bash
# 启动后端
cd backend && python app.py

# 启动前端
cd frontend && npm run serve
```

5. 访问系统
- 前端地址: http://localhost:8080
- 后端API: http://localhost:5000

## 开发说明

详细的开发文档请参考 `docs/` 目录下的相关文档。

## 许可证

MIT License 