#!/bin/bash

# 智能行为检测系统启动脚本
# 作者: behavior-detection-team
# 版本: 1.0.0

echo "=========================================="
echo "  智能行为检测系统 - 启动脚本"
echo "=========================================="

# 检查Python环境
echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python 3.8或更高版本"
    exit 1
fi

python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Python版本: $python_version"

# 检查Node.js环境
echo "检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装Node.js 16或更高版本"
    exit 1
fi

node_version=$(node -v)
echo "✓ Node.js版本: $node_version"

# 检查npm环境
if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装，请先安装npm"
    exit 1
fi

npm_version=$(npm -v)
echo "✓ npm版本: $npm_version"

# 创建必要的目录
echo "创建项目目录..."
mkdir -p uploads outputs logs database

# 后端环境检查和启动
echo "=========================================="
echo "准备启动后端服务..."
echo "=========================================="

cd backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装Python依赖
echo "安装Python依赖包..."
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✓ Python依赖安装完成"
else
    echo "⚠ requirements.txt 文件不存在，跳过依赖安装"
fi

# 检查算法模块
echo "检查算法模块..."
if [ -d "../yolo_slowfast-master" ]; then
    echo "✓ 算法模块存在"
else
    echo "⚠ 算法模块不存在，某些功能可能无法正常工作"
fi

# 启动后端服务
echo "启动后端Flask服务..."
nohup python app.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ 后端服务已启动，PID: $BACKEND_PID"

cd ..

# 前端环境检查和启动
echo "=========================================="
echo "准备启动前端服务..."
echo "=========================================="

cd frontend

# 检查前端依赖
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖包..."
    npm install
    echo "✓ 前端依赖安装完成"
else
    echo "✓ 前端依赖已存在"
fi

# 启动前端开发服务器
echo "启动前端Vue服务..."
nohup npm run serve > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✓ 前端服务已启动，PID: $FRONTEND_PID"

cd ..

# 保存进程ID到文件
echo $BACKEND_PID > .backend_pid
echo $FRONTEND_PID > .frontend_pid

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "=========================================="
echo "检查服务状态..."
echo "=========================================="

# 检查后端服务
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✓ 后端服务运行正常: http://localhost:5000"
else
    echo "⚠ 后端服务可能启动失败，请检查日志: logs/backend.log"
fi

# 检查前端服务
if curl -s http://localhost:8080 > /dev/null; then
    echo "✓ 前端服务运行正常: http://localhost:8080"
else
    echo "⚠ 前端服务可能启动失败，请检查日志: logs/frontend.log"
fi

echo "=========================================="
echo "系统启动完成！"
echo "=========================================="
echo "📱 前端地址: http://localhost:8080"
echo "🔧 后端API: http://localhost:5000"
echo "📋 健康检查: http://localhost:5000/api/health"
echo ""
echo "📝 日志文件："
echo "   - 后端日志: logs/backend.log"
echo "   - 前端日志: logs/frontend.log"
echo "   - 应用日志: logs/app.log"
echo ""
echo "🛑 停止服务: ./stop.sh"
echo "🔄 重启服务: ./restart.sh"
echo ""
echo "💡 提示："
echo "   - 首次启动可能需要下载模型文件，请耐心等待"
echo "   - 如果遇到权限问题，请运行: chmod +x *.sh"
echo "   - 如果后端启动失败，请检查算法模块是否完整"
echo "=========================================="

# 显示实时日志（可选）
echo "是否显示实时日志？(y/n)"
read -t 10 -n 1 show_logs
echo ""

if [ "$show_logs" = "y" ] || [ "$show_logs" = "Y" ]; then
    echo "显示实时日志（按 Ctrl+C 退出）..."
    tail -f logs/backend.log logs/frontend.log
fi 