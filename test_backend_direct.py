#!/usr/bin/env python3
"""
直接测试后端API逻辑
"""
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import db, DetectionTask
from flask import Flask
import json

def test_task_api_logic():
    """直接测试任务API逻辑"""
    app = Flask(__name__)
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'behavior_detection.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        # 获取第一个任务
        task = DetectionTask.query.first()
        if not task:
            print("❌ 没有找到任务")
            return
            
        print(f"✓ 找到任务: {task.id}")
        print(f"  - 任务名称: {task.task_name}")
        print(f"  - 源路径: {task.source_path}")
        
        # 测试to_dict方法
        task_dict = task.to_dict()
        print(f"  - to_dict结果: {json.dumps(task_dict, indent=2, ensure_ascii=False)}")
        
        # 测试文件大小计算
        file_size = 0
        try:
            if task.source_path:
                print(f"  - 检查文件路径: {task.source_path}")
                print(f"  - 文件存在: {os.path.exists(task.source_path)}")
                if os.path.exists(task.source_path):
                    file_size = os.path.getsize(task.source_path)
                    print(f"  - 文件大小: {file_size} bytes")
                else:
                    print(f"  - 文件不存在")
            else:
                print("  - 源路径为空")
        except Exception as e:
            print(f"  - 计算文件大小失败: {e}")
            file_size = 0
        
        # 添加文件大小到返回数据
        task_dict['file_size'] = file_size
        
        print(f"✓ 最终API返回数据:")
        print(json.dumps({
            'success': True,
            'task': task_dict
        }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_task_api_logic()
