#!/usr/bin/env python3
"""
简单测试后端API
"""
import requests
import time

def test_simple():
    """简单测试"""
    base_url = "http://localhost:5001"
    
    # 等待后端启动
    print("等待后端启动...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/api/health", timeout=2)
            if response.status_code == 200:
                print("✓ 后端已启动")
                break
        except:
            print(f"等待中... {i+1}/10")
            time.sleep(2)
    else:
        print("❌ 后端启动超时")
        return
    
    # 测试任务详情API
    try:
        print("🔍 测试任务详情API...")
        response = requests.get(f"{base_url}/api/tasks/2", timeout=5)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {data}")
            if data.get('success'):
                task = data['task']
                print(f"✓ 任务详情获取成功")
                print(f"  - 文件大小: {task.get('file_size')}")
            else:
                print(f"❌ API返回错误: {data.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_simple()
