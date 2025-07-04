#!/usr/bin/env python3
"""
检查数据库中的任务信息
"""
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import db, DetectionTask
from flask import Flask

def check_database():
    """检查数据库中的任务信息"""
    app = Flask(__name__)
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'behavior_detection.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        tasks = DetectionTask.query.all()
        print(f"数据库中共有 {len(tasks)} 个任务:")
        
        for task in tasks:
            print(f"\n任务ID: {task.id}")
            print(f"任务名称: {task.task_name}")
            print(f"源路径: {task.source_path}")
            print(f"文件存在: {os.path.exists(task.source_path) if task.source_path else False}")
            if task.source_path and os.path.exists(task.source_path):
                file_size = os.path.getsize(task.source_path)
                print(f"文件大小: {file_size} bytes")
            print(f"置信度: {task.confidence_threshold}")
            print(f"输入尺寸: {task.input_size}")
            print(f"设备: {task.device}")
            print(f"状态: {task.status}")
            print(f"创建时间: {task.created_at}")
            print(f"开始时间: {task.started_at}")
            print(f"完成时间: {task.completed_at}")

if __name__ == "__main__":
    check_database()
