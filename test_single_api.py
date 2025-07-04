#!/usr/bin/env python3
"""
测试单个API调用
"""
import requests
import json

def test_single_api():
    """测试单个API调用"""
    try:
        print("🔍 调用任务详情API...")
        response = requests.get("http://localhost:5001/api/tasks/2", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ JSON解析成功")
            print(f"成功标志: {data.get('success')}")
            if data.get('success'):
                task = data['task']
                print(f"任务字段: {list(task.keys())}")
                print(f"文件大小字段: {'file_size' in task}")
                if 'file_size' in task:
                    print(f"文件大小值: {task['file_size']}")
        else:
            print(f"❌ HTTP错误")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    test_single_api()
