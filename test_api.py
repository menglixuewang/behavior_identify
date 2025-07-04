#!/usr/bin/env python3
"""
测试任务详情API的脚本
"""
import requests
import json
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_task_detail_api():
    """测试任务详情API"""
    base_url = "http://localhost:5001"
    
    try:
        # 首先获取任务列表
        print("🔍 获取任务列表...")
        response = requests.get(f"{base_url}/api/tasks")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('tasks'):
                task_id = data['tasks'][0]['id']
                print(f"✓ 找到任务ID: {task_id}")
                
                # 测试获取任务详情
                print(f"🔍 获取任务 {task_id} 的详情...")
                detail_response = requests.get(f"{base_url}/api/tasks/{task_id}")
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    if detail_data.get('success'):
                        task_detail = detail_data['task']
                        print("✓ 任务详情获取成功:")
                        print(f"  - 任务名称: {task_detail.get('task_name')}")
                        print(f"  - 置信度阈值: {task_detail.get('confidence_threshold')}")
                        print(f"  - 输入尺寸: {task_detail.get('input_size')}")
                        print(f"  - 设备类型: {task_detail.get('device')}")
                        print(f"  - 文件大小: {task_detail.get('file_size')} bytes")
                        print(f"  - 创建时间: {task_detail.get('created_at')}")
                        print(f"  - 开始时间: {task_detail.get('started_at')}")
                        print(f"  - 完成时间: {task_detail.get('completed_at')}")
                        
                        # 检查缺失的字段
                        missing_fields = []
                        required_fields = ['confidence_threshold', 'input_size', 'device', 'file_size']
                        for field in required_fields:
                            if task_detail.get(field) is None:
                                missing_fields.append(field)
                        
                        if missing_fields:
                            print(f"⚠ 缺失字段: {missing_fields}")
                        else:
                            print("✓ 所有必需字段都存在")
                            
                    else:
                        print(f"❌ 获取任务详情失败: {detail_data.get('error')}")
                else:
                    print(f"❌ API请求失败: {detail_response.status_code}")
            else:
                print("❌ 没有找到任务")
        else:
            print(f"❌ 获取任务列表失败: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_task_detail_api()
