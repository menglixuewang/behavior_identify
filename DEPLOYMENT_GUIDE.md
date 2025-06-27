# 智能行为检测系统部署指南

## 📋 目录
- [系统概述](#系统概述)
- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [运行监控](#运行监控)
- [故障排除](#故障排除)

## 🎯 系统概述

智能行为检测系统是基于YOLOv8+SlowFast算法的实时视频行为识别系统，支持：

- 📹 实时摄像头监控
- 🎥 视频文件检测
- 🚨 异常行为报警
- 📊 数据统计分析
- 💻 Web界面管理

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   后端API       │    │   算法模块      │
│   Vue.js        │◄──►│   Flask         │◄──►│   YOLOv8        │
│   Element Plus  │    │   SQLite        │    │   SlowFast      │
│   Socket.IO     │    │   WebSocket     │    │   DeepSort      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 💻 环境要求

### 基础环境
- **操作系统**: Linux/macOS/Windows
- **Python**: 3.8+ (推荐3.9+)
- **Node.js**: 16+ (推荐18+)
- **内存**: 最低8GB，推荐16GB+
- **存储空间**: 最低10GB可用空间

### Python依赖
```bash
Flask>=2.3.3
torch>=2.0.0
ultralytics>=8.0.0
opencv-python>=4.8.0
numpy>=1.24.0
```

### Node.js依赖
```bash
vue@^3.3.8
element-plus@^2.4.2
axios@^1.6.0
socket.io-client@^4.7.4
```

## 🚀 快速部署

### 方法一：一键启动脚本（推荐）

```bash
# 1. 给脚本添加执行权限
chmod +x start.sh stop.sh

# 2. 启动系统
./start.sh

# 3. 访问系统
# 前端: http://localhost:8080
# 后端: http://localhost:5000
```

### 方法二：Docker部署（即将支持）

```bash
# 构建并启动容器
docker-compose up -d

# 查看服务状态
docker-compose ps

# 停止服务
docker-compose down
```

## 🔧 手动部署

### 后端部署

1. **创建虚拟环境**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

2. **安装依赖**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
export FLASK_ENV=development
export DATABASE_URL=sqlite:///behavior_detection.db
```

4. **启动后端服务**
```bash
python app.py
```

### 前端部署

1. **安装依赖**
```bash
cd frontend
npm install
```

2. **启动开发服务器**
```bash
npm run serve
```

3. **构建生产版本**
```bash
npm run build
```

## ⚙️ 配置说明

### 后端配置文件

位置：`backend/config/config.py`

```python
class Config:
    # 基础配置
    SECRET_KEY = 'your-secret-key'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///behavior_detection.db'
    
    # 检测参数
    CONFIDENCE_THRESHOLD = 0.5
    INPUT_SIZE = 640
    DEVICE = 'cpu'  # 或 'cuda'
    
    # 报警配置
    ALERT_BEHAVIORS = ['fall down', 'fight', 'enter', 'exit']
```

### 前端配置文件

位置：`frontend/src/config/index.js`

```javascript
export default {
  // API基础地址
  apiBaseUrl: 'http://localhost:5000',
  
  // WebSocket地址
  websocketUrl: 'http://localhost:5000',
  
  // 上传配置
  uploadConfig: {
    maxFileSize: 500 * 1024 * 1024, // 500MB
    allowedTypes: ['mp4', 'avi', 'mov']
  }
}
```

### 算法模型配置

1. **YOLOv8模型**
   - 模型文件：`yolov8n.pt`
   - 支持的尺寸：416, 640, 832
   - 置信度阈值：0.1-1.0

2. **SlowFast模型**
   - 权重文件：`SLOWFAST_8x8_R50_DETECTION.pyth`
   - 输入帧数：25帧
   - 行为类别：80+种

3. **DeepSort追踪**
   - 权重文件：`ckpt.t7`
   - 特征维度：128维
   - 最大跟踪距离：0.2

## 📊 运行监控

### 系统状态检查

```bash
# 检查后端服务
curl http://localhost:5000/api/health

# 检查前端服务
curl http://localhost:8080

# 查看系统统计
curl http://localhost:5000/api/statistics
```

### 日志监控

```bash
# 查看实时日志
tail -f logs/app.log

# 查看后端日志
tail -f logs/backend.log

# 查看前端日志
tail -f logs/frontend.log
```

### 性能监控

```bash
# CPU和内存使用情况
htop

# GPU使用情况（如果有）
nvidia-smi

# 磁盘空间
df -h
```

## 🛠️ 故障排除

### 常见问题

#### 1. 后端启动失败

**症状**: Flask服务无法启动
**原因**: 依赖包缺失或版本不兼容

```bash
# 解决方案
pip install --upgrade -r requirements.txt
pip list | grep -E "(torch|opencv|flask)"
```

#### 2. 算法模型加载失败

**症状**: 检测功能不可用
**原因**: 模型文件缺失或路径错误

```bash
# 检查模型文件
ls yolo_slowfast-master/
ls yolo_slowfast-master/deep_sort/deep_sort/deep/checkpoint/

# 下载缺失的模型文件
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

#### 3. 前端构建失败

**症状**: npm run serve报错
**原因**: Node.js版本过低或依赖冲突

```bash
# 解决方案
node --version  # 确保16+
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 4. 端口被占用

**症状**: 服务启动时提示端口占用
**原因**: 端口5000或8080被其他进程占用

```bash
# 查找并停止占用进程
lsof -ti:5000 | xargs kill -9
lsof -ti:8080 | xargs kill -9

# 或使用停止脚本
./stop.sh
```

#### 5. 摄像头无法访问

**症状**: 实时监控无法启动
**原因**: 摄像头权限或驱动问题

```bash
# Linux下检查摄像头
ls /dev/video*
v4l2-ctl --list-devices

# macOS下检查权限
# 系统偏好设置 > 安全性与隐私 > 摄像头
```

### 调试模式

启用调试模式获取详细日志：

```bash
# 后端调试模式
export FLASK_DEBUG=1
python app.py

# 前端调试模式
npm run serve -- --mode development
```

### 数据库问题

如果数据库出现问题，可以重新初始化：

```bash
# 备份现有数据
cp behavior_detection.db behavior_detection.db.backup

# 删除数据库文件
rm behavior_detection.db

# 重启服务，数据库将自动重新创建
./start.sh
```

## 📞 技术支持

如果遇到无法解决的问题，请：

1. 查看详细的错误日志
2. 检查环境配置是否正确
3. 确认所有依赖是否安装完整
4. 参考GitHub Issues或联系技术支持

## 🔄 版本更新

```bash
# 停止服务
./stop.sh

# 拉取最新代码
git pull origin main

# 更新依赖
cd backend && pip install -r requirements.txt
cd ../frontend && npm install

# 重启服务
./start.sh
```

---

**⚠️ 注意事项**

1. 生产环境建议使用HTTPS
2. 定期备份数据库和配置文件
3. 监控系统资源使用情况
4. 及时更新安全补丁
5. 设置适当的日志轮转策略 