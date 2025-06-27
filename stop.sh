#!/bin/bash

# 智能行为检测系统停止脚本
# 作者: behavior-detection-team
# 版本: 1.0.0

echo "=========================================="
echo "  智能行为检测系统 - 停止脚本"
echo "=========================================="

# 停止后端服务
if [ -f ".backend_pid" ]; then
    BACKEND_PID=$(cat .backend_pid)
    echo "停止后端服务 (PID: $BACKEND_PID)..."
    
    if ps -p $BACKEND_PID > /dev/null; then
        kill $BACKEND_PID
        echo "✓ 后端服务已停止"
    else
        echo "⚠ 后端服务进程不存在"
    fi
    
    rm -f .backend_pid
else
    echo "⚠ 未找到后端服务PID文件"
fi

# 停止前端服务
if [ -f ".frontend_pid" ]; then
    FRONTEND_PID=$(cat .frontend_pid)
    echo "停止前端服务 (PID: $FRONTEND_PID)..."
    
    if ps -p $FRONTEND_PID > /dev/null; then
        kill $FRONTEND_PID
        echo "✓ 前端服务已停止"
    else
        echo "⚠ 前端服务进程不存在"
    fi
    
    rm -f .frontend_pid
else
    echo "⚠ 未找到前端服务PID文件"
fi

# 清理端口（强制停止占用端口的进程）
echo "检查端口占用..."

# 检查5000端口（后端）
BACKEND_PORT_PID=$(lsof -t -i:5000 2>/dev/null)
if [ ! -z "$BACKEND_PORT_PID" ]; then
    echo "强制停止占用5000端口的进程: $BACKEND_PORT_PID"
    kill -9 $BACKEND_PORT_PID
fi

# 检查8080端口（前端）
FRONTEND_PORT_PID=$(lsof -t -i:8080 2>/dev/null)
if [ ! -z "$FRONTEND_PORT_PID" ]; then
    echo "强制停止占用8080端口的进程: $FRONTEND_PORT_PID"
    kill -9 $FRONTEND_PORT_PID
fi

echo "=========================================="
echo "系统已完全停止！"
echo "=========================================="
echo "所有服务进程已终止"
echo "端口5000和8080已释放"
echo ""
echo "🔄 重新启动系统: ./start.sh"
echo "==========================================" 