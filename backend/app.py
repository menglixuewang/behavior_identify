"""
智能行为检测系统 - Flask应用主文件
"""
import os
import sys
import time
import json
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect, join_room, leave_room
import threading
from engineio.async_drivers import gevent
import traceback

hiddenimports=[
    "gevent",                    # 核心协程库
    "geventwebsocket",           # WebSocket 支持
    "gevent.ssl",                # SSL 加密支持
    "gevent.builtins",           # 替换 Python 内置函数
    "engineio.async_drivers.threading"  # 强制指定线程模式驱动
]

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入项目模块
try:
    from config.config import config
    from models.database import db, DetectionTask, DetectionResult, AlertRecord, SystemConfig, SystemLog, create_tables
    from services.detection_service import get_detection_service
    from utils.logger import setup_logger
    from utils.file_utils import allowed_file, get_file_size, cleanup_old_files
except ImportError as e:
    print(f"导入模块失败: {e}")


def create_app(config_name='development'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化扩展
    db.init_app(app)
    CORS(app)
    
    # 初始化SocketIO
    socketio = SocketIO(app, 
                       cors_allowed_origins="*", 
                       async_mode='eventlet',
                       logger=True, 
                       engineio_logger=True)
    
    # 设置日志
    logger = setup_logger(app.config['LOG_FILE'], app.config['LOG_LEVEL'])
    
    # 存储WebSocket连接
    websocket_clients = {}
    
    # 创建数据库表
    with app.app_context():
        create_tables()
    
    # ========================= REST API 路由 =========================
    
    @app.route('/')
    def index():
        """首页"""
        return jsonify({
            'message': '智能行为检测系统API',
            'version': '1.0.0',
            'status': 'running',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/health')
    def health_check():
        """健康检查"""
        try:
            # 检查数据库连接
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db_status = 'ok'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        return jsonify({
            'status': 'healthy',
            'database': db_status,
            'timestamp': datetime.now().isoformat()
        })
    
    # ========================= 文件上传API =========================
    
    @app.route('/api/upload', methods=['POST'])
    def upload_video():
        """上传视频文件"""
        try:
            if 'video' not in request.files:
                return jsonify({'error': '没有上传文件'}), 400
            
            file = request.files['video']
            if file.filename == '':
                return jsonify({'error': '未选择文件'}), 400
            
            if not allowed_file(file.filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
                return jsonify({'error': '不支持的文件格式'}), 400
            
            # 检查文件大小
            if get_file_size(file) > app.config['MAX_CONTENT_LENGTH']:
                return jsonify({'error': '文件大小超出限制'}), 400
            
            # 保存文件
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            file.save(file_path)
            
            # 创建检测任务
            task = DetectionTask(
                task_name=request.form.get('task_name', filename),
                source_type='video',
                source_path=file_path,
                confidence_threshold=float(request.form.get('confidence', 0.5)),
                input_size=int(request.form.get('input_size', 640)),
                device=request.form.get('device', 'cpu')
            )
            
            db.session.add(task)
            db.session.commit()
            
            logger.info(f"视频上传成功: {filename}, 任务ID: {task.id}")
            
            return jsonify({
                'success': True,
                'taskId': task.id,  # 使用驼峰命名匹配前端
                'task_id': task.id,  # 保持向后兼容
                'filename': safe_filename,
                'file_path': file_path,
                'message': '视频上传成功'
            })
            
        except Exception as e:
            logger.error(f"视频上传失败: {str(e)}")
            return jsonify({'error': f'上传失败: {str(e)}'}), 500
    
    @app.route('/api/detect/video', methods=['POST'])
    def start_video_detection():
        """启动视频检测"""
        try:
            data = request.get_json()
            task_id = data.get('task_id')
            
            if not task_id:
                return jsonify({'error': '缺少任务ID'}), 400
            
            # 获取任务信息
            task = DetectionTask.query.get(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            
            if task.status != 'pending':
                return jsonify({'error': f'任务状态错误: {task.status}'}), 400
            
            # 检查文件是否存在
            if not os.path.exists(task.source_path):
                return jsonify({'error': '源文件不存在'}), 404
            
            # 准备输出路径
            output_filename = f"result_{task.id}_{int(time.time())}.mp4"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            task.output_path = output_path
            
            # 更新任务状态
            task.status = 'running'
            task.started_at = datetime.utcnow()
            db.session.commit()
            
            # 启动检测线程
            def detection_worker():
                current_task = task  # 保存当前任务引用，避免作用域问题
                try:
                    # 在检测线程中创建应用上下文
                    with app.app_context():
                        detection_service = get_detection_service({
                            'device': current_task.device,
                            'input_size': current_task.input_size,
                            'confidence_threshold': current_task.confidence_threshold
                        })
                        
                        def progress_callback(task_id, progress):
                            # 确保在应用上下文中更新数据库
                            with app.app_context():
                                task_obj = DetectionTask.query.get(task_id)
                                if task_obj:
                                    task_obj.progress = progress
                                    db.session.commit()
                            
                            # 通过WebSocket发送进度更新
                            socketio.emit('progress_update', {
                                'task_id': task_id,
                                'progress': progress
                            }, namespace='/detection')
                        
                        # 执行检测
                        result = detection_service.detect_video(
                            current_task.source_path,
                            output_path,
                            progress_callback
                        )
                    
                        if result['success']:
                            # 保存检测结果到数据库 (在应用上下文中)
                            with app.app_context():
                                task_obj = DetectionTask.query.get(current_task.id)
                                if task_obj:
                                    for detection in result['results']:
                                        detection_result = DetectionResult(
                                            task_id=task_obj.id,
                                            frame_number=detection['frame_number'],
                                            timestamp=detection['timestamp'],
                                            object_id=detection.get('object_id'),
                                            object_type=detection['object_type'],
                                            confidence=detection['confidence'],
                                            bbox_x1=detection['bbox']['x1'],
                                            bbox_y1=detection['bbox']['y1'],
                                            bbox_x2=detection['bbox']['x2'],
                                            bbox_y2=detection['bbox']['y2'],
                                            behavior_type=detection.get('behavior_type'),
                                            is_anomaly=detection.get('is_anomaly', False)
                                        )
                                        db.session.add(detection_result)
                                        
                                        # 如果是异常行为，创建报警记录
                                        if detection.get('is_anomaly'):
                                            alert = AlertRecord(
                                                task_id=task_obj.id,
                                                alert_type=detection['behavior_type'],
                                                trigger_frame=detection['frame_number'],
                                                trigger_timestamp=detection['timestamp'],
                                                trigger_object_id=detection.get('object_id'),
                                                trigger_behavior=detection['behavior_type'],
                                                trigger_confidence=detection['confidence'],
                                                description=f"检测到异常行为: {detection['behavior_type']}"
                                            )
                                            db.session.add(alert)
                                    
                                    # 更新任务状态
                                    task_obj.status = 'completed'
                                    task_obj.completed_at = datetime.utcnow()
                                    task_obj.progress = 100.0
                                    task_obj.detected_objects = len(result['results'])
                                    task_obj.detected_behaviors = len([r for r in result['results'] if r.get('behavior_type')])
                                    db.session.commit()
                                    
                                    print(f"✓ 任务 {task_obj.id} 检测完成，结果已保存")
                            
                        else:
                            # 更新失败状态 (在应用上下文中)
                            with app.app_context():
                                task_obj = DetectionTask.query.get(current_task.id)
                                if task_obj:
                                    task_obj.status = 'failed'
                                    task_obj.error_message = result['error']
                                    db.session.commit()
                                    print(f"❌ 任务 {task_obj.id} 检测失败: {result['error']}")
                    
                    # 通过WebSocket发送完成通知
                    socketio.emit('task_completed', {
                        'task_id': task.id,
                        'status': task.status,
                        'message': '检测完成' if result['success'] else f"检测失败: {result['error']}"
                    }, namespace='/detection')
                    
                except Exception as e:
                    logger.error(f"检测任务执行失败: {str(e)}")
                    # 更新失败状态 (在应用上下文中)
                    with app.app_context():
                        task_obj = DetectionTask.query.get(current_task.id)
                        if task_obj:
                            task_obj.status = 'failed'
                            task_obj.error_message = str(e)
                            db.session.commit()
                    
                    socketio.emit('task_failed', {
                        'task_id': current_task.id,
                        'error': str(e)
                    }, namespace='/detection')
                    
                    print(f"❌ 检测任务异常: {str(e)}")
            
            # 启动检测线程
            thread = threading.Thread(target=detection_worker, daemon=True)
            thread.start()
            
            return jsonify({
                'success': True,
                'taskId': task.id,  # 使用驼峰命名匹配前端
                'task_id': task.id,  # 保持向后兼容
                'message': '检测任务已启动'
            })
            
        except Exception as e:
            logger.error(f"启动视频检测失败: {str(e)}")
            return jsonify({'error': f'启动失败: {str(e)}'}), 500
    
    @app.route('/api/detect/realtime', methods=['POST'])
    def start_realtime_detection():
        """启动实时检测"""
        try:
            data = request.get_json()
            source = data.get('source', 0)  # 摄像头ID
            
            # 创建实时检测任务
            task = DetectionTask(
                task_name=f"实时检测_{int(time.time())}",
                source_type='camera',
                source_path=str(source),
                confidence_threshold=float(data.get('confidence', 0.5)),
                input_size=int(data.get('input_size', 640)),
                device=data.get('device', 'cpu')
            )
            
            db.session.add(task)
            db.session.commit()
            
            # 启动实时检测
            detection_service = get_detection_service({
                'device': task.device,
                'input_size': task.input_size,
                'confidence_threshold': task.confidence_threshold
            })
            
            def websocket_callback(data):
                """WebSocket回调函数"""
                socketio.emit('realtime_result', data, namespace='/detection')
                
                # 如果是报警，记录到数据库
                if data.get('type') == 'alert':
                    detection = data['detection']
                    alert = AlertRecord(
                        task_id=task.id,
                        alert_type=data['alert_type'],
                        trigger_frame=detection['frame_number'],
                        trigger_timestamp=detection['timestamp'],
                        trigger_object_id=detection.get('object_id'),
                        trigger_behavior=detection['behavior_type'],
                        trigger_confidence=detection['confidence'],
                        description=f"实时检测到异常行为: {data['alert_type']}"
                    )
                    db.session.add(alert)
                    db.session.commit()
            
            service_task_id = detection_service.start_realtime_detection(source, websocket_callback)
            
            # 更新任务状态
            task.status = 'running'
            task.started_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'service_task_id': service_task_id,
                'message': '实时检测已启动'
            })
            
        except Exception as e:
            logger.error(f"启动实时检测失败: {str(e)}")
            return jsonify({'error': f'启动失败: {str(e)}'}), 500
    
    @app.route('/api/detect/stop/<int:task_id>', methods=['POST'])
    def stop_detection(task_id):
        """停止检测任务"""
        try:
            task = DetectionTask.query.get(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            
            if task.status not in ['running', 'pending']:
                return jsonify({'error': f'任务状态错误: {task.status}'}), 400
            
            # 如果是实时检测，停止检测服务
            if task.source_type == 'camera':
                detection_service = get_detection_service()
                # 这里需要实现停止实时检测的逻辑
                pass
            
            # 更新任务状态
            task.status = 'stopped'
            task.completed_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '任务已停止'
            })
            
        except Exception as e:
            logger.error(f"停止检测失败: {str(e)}")
            return jsonify({'error': f'停止失败: {str(e)}'}), 500
    
    # ========================= 数据查询API =========================
    
    @app.route('/api/tasks', methods=['GET'])
    def get_tasks():
        """获取任务列表"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            status = request.args.get('status')
            task_type = request.args.get('type')  # 添加type参数处理
            
            query = DetectionTask.query
            if status:
                query = query.filter(DetectionTask.status == status)
            if task_type:
                query = query.filter(DetectionTask.source_type == task_type)
            
            pagination = query.order_by(DetectionTask.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 转换为前端期望的格式
            tasks = []
            for task in pagination.items:
                # 计算文件大小
                file_size = 0
                try:
                    if task.source_path and os.path.exists(task.source_path):
                        file_size = os.path.getsize(task.source_path)
                except Exception:
                    file_size = 0
                
                task_data = {
                    'id': task.id,
                    'filename': task.task_name,  # 使用task_name作为filename
                    'size': file_size,  # 计算文件大小
                    'status': task.status,
                    'detections': task.detected_objects or 0,  # 使用detected_objects作为detections
                    'uploadTime': task.created_at.isoformat() if task.created_at else None,  # 使用created_at作为uploadTime
                    'progress': task.progress,
                    'source_type': task.source_type
                }
                tasks.append(task_data)
            
            return jsonify({
                'success': True,
                'tasks': tasks,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            })
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return jsonify({'error': f'获取失败: {str(e)}'}), 500
    
    @app.route('/api/tasks/<int:task_id>')
    def get_task(task_id):
        """获取单个任务详情"""
        try:
            task = DetectionTask.query.get(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            
            return jsonify({
                'success': True,
                'task': task.to_dict()
            })
            
        except Exception as e:
            logger.error(f"获取任务详情失败: {str(e)}")
            return jsonify({'error': f'获取失败: {str(e)}'}), 500
    
    @app.route('/api/tasks/<int:task_id>/results')
    def get_task_results(task_id):
        """获取任务完整结果（包含视频和统计信息）"""
        try:
            # 获取任务信息
            task = DetectionTask.query.get(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            
            # 获取检测结果
            results = DetectionResult.query.filter_by(task_id=task_id).all()
            
            # 计算统计信息
            total_detections = len(results)
            detected_frames = len(set(result.frame_number for result in results))
            alert_count = sum(1 for result in results if result.is_anomaly)
            
            # 行为分析
            behavior_stats = {}
            for result in results:
                behavior = result.behavior_type or 'unknown'
                if behavior not in behavior_stats:
                    behavior_stats[behavior] = {
                        'count': 0,
                        'confidence_sum': 0,
                        'frames': []
                    }
                behavior_stats[behavior]['count'] += 1
                behavior_stats[behavior]['confidence_sum'] += result.confidence
                behavior_stats[behavior]['frames'].append(result.frame_number)
            
            behaviors = []
            for behavior, stats in behavior_stats.items():
                avg_confidence = stats['confidence_sum'] / stats['count'] if stats['count'] > 0 else 0
                duration = (max(stats['frames']) - min(stats['frames'])) / 25.0 if stats['frames'] else 0
                behaviors.append({
                    'behavior': behavior,
                    'count': stats['count'],
                    'confidence': f"{avg_confidence:.2f}",
                    'duration': f"{duration:.1f}s"
                })
            
            # 构建视频URL
            video_url = None
            if task.output_path and os.path.exists(task.output_path):
                filename = os.path.basename(task.output_path)
                video_url = f"http://localhost:5000/api/outputs/{filename}"
            
            # 返回完整结果
            return jsonify({
                'success': True,
                'filename': task.task_name,
                'videoUrl': video_url,
                'downloadUrl': f"http://localhost:5000/api/download/result/{task_id}",
                'totalFrames': task.total_frames or 0,
                'detectedFrames': detected_frames,
                'totalDetections': total_detections,
                'alertCount': alert_count,
                'behaviors': behaviors,
                'task': task.to_dict(),
                'results': [result.to_dict() for result in results[:50]]  # 限制返回数量
            })
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {str(e)}")
            return jsonify({'error': f'获取失败: {str(e)}'}), 500
    
    @app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
    def delete_task(task_id):
        """删除任务及相关数据"""
        try:
            task = DetectionTask.query.get(task_id)
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            
            # 删除相关的检测结果
            DetectionResult.query.filter_by(task_id=task_id).delete()
            
            # 删除相关的报警记录
            AlertRecord.query.filter_by(task_id=task_id).delete()
            
            # 删除输出文件
            if task.output_path and os.path.exists(task.output_path):
                try:
                    os.remove(task.output_path)
                    logger.info(f"删除输出文件: {task.output_path}")
                except Exception as e:
                    logger.warning(f"删除输出文件失败: {e}")
            
            # 删除上传文件
            if task.source_path and os.path.exists(task.source_path):
                try:
                    os.remove(task.source_path)
                    logger.info(f"删除源文件: {task.source_path}")
                except Exception as e:
                    logger.warning(f"删除源文件失败: {e}")
            
            # 删除任务记录
            db.session.delete(task)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '任务删除成功'
            })
            
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'删除失败: {str(e)}'}), 500
    
    @app.route('/api/alerts')
    def get_alerts():
        """获取报警记录"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            status = request.args.get('status')
            
            query = AlertRecord.query
            if status:
                query = query.filter(AlertRecord.status == status)
            
            pagination = query.order_by(AlertRecord.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            alerts = [alert.to_dict() for alert in pagination.items]
            
            return jsonify({
                'success': True,
                'alerts': alerts,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            })
            
        except Exception as e:
            logger.error(f"获取报警记录失败: {str(e)}")
            return jsonify({'error': f'获取失败: {str(e)}'}), 500
    
    @app.route('/api/statistics')
    def get_statistics():
        """获取系统统计信息"""
        try:
            # 任务统计
            total_tasks = DetectionTask.query.count()
            running_tasks = DetectionTask.query.filter_by(status='running').count()
            completed_tasks = DetectionTask.query.filter_by(status='completed').count()
            failed_tasks = DetectionTask.query.filter_by(status='failed').count()
            
            # 报警统计
            total_alerts = AlertRecord.query.count()
            active_alerts = AlertRecord.query.filter_by(status='active').count()
            
            # 今日统计
            today = datetime.now().date()
            today_tasks = DetectionTask.query.filter(
                DetectionTask.created_at >= today
            ).count()
            today_alerts = AlertRecord.query.filter(
                AlertRecord.created_at >= today
            ).count()
            
            return jsonify({
                'success': True,
                'statistics': {
                    'tasks': {
                        'total': total_tasks,
                        'running': running_tasks,
                        'completed': completed_tasks,
                        'failed': failed_tasks,
                        'today': today_tasks
                    },
                    'alerts': {
                        'total': total_alerts,
                        'active': active_alerts,
                        'today': today_alerts
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return jsonify({'error': f'获取失败: {str(e)}'}), 500
    
    # ========================= 文件下载API =========================
    
    @app.route('/api/download/result/<int:task_id>')
    def download_result(task_id):
        """下载检测结果视频"""
        try:
            task = DetectionTask.query.get(task_id)
            if not task or not task.output_path:
                return jsonify({'error': '文件不存在'}), 404
            
            if not os.path.exists(task.output_path):
                return jsonify({'error': '文件不存在'}), 404
            
            return send_file(
                task.output_path,
                as_attachment=True,
                download_name=f"result_{task_id}.mp4"
            )
            
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            return jsonify({'error': f'下载失败: {str(e)}'}), 500
    
    # ========================= 静态文件服务 =========================
    
    @app.route('/api/outputs/<filename>')
    def serve_output_file(filename):
        """提供输出视频文件的静态访问，支持Range请求"""
        try:
            # 添加调试日志
            logger.info(f"请求静态文件: {filename}")
            
            # 使用应用程序所在目录作为基准路径，确保正确找到outputs文件夹
            current_dir = os.path.dirname(os.path.abspath(__file__))
            outputs_path = os.path.join(current_dir, 'outputs')
            file_path = os.path.join(outputs_path, filename)
            
            logger.info(f"文件路径: {file_path}")
            logger.info(f"当前工作目录: {os.getcwd()}")
            logger.info(f"outputs目录: {outputs_path}")
            logger.info(f"文件存在: {os.path.exists(file_path)}")
            
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return jsonify({'error': '文件不存在', 'path': file_path}), 404
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            logger.info(f"文件大小: {file_size} bytes")
            
            # 处理Range请求（视频播放必需）
            range_header = request.headers.get('Range')
            if range_header:
                logger.info(f"Range请求: {range_header}")
                # 解析Range头
                byte_start = 0
                byte_end = file_size - 1
                
                if range_header.startswith('bytes='):
                    range_match = range_header[6:].split('-')
                    if range_match[0]:
                        byte_start = int(range_match[0])
                    if range_match[1]:
                        byte_end = int(range_match[1])
                
                # 确保范围有效
                byte_start = max(0, byte_start)
                byte_end = min(file_size - 1, byte_end)
                content_length = byte_end - byte_start + 1
                
                # 读取指定范围的数据
                with open(file_path, 'rb') as f:
                    f.seek(byte_start)
                    data = f.read(content_length)
                
                # 设置MIME类型
                if filename.endswith('.avi'):
                    mimetype = 'video/x-msvideo'
                elif filename.endswith('.mp4'):
                    mimetype = 'video/mp4'
                elif filename.endswith('.webm'):
                    mimetype = 'video/webm'
                else:
                    mimetype = 'video/mp4'
                
                logger.info(f"返回Range响应: {byte_start}-{byte_end}/{file_size}")
                
                # 创建Range响应
                response = Response(
                    data,
                    206,  # Partial Content
                    headers={
                        'Content-Type': mimetype,
                        'Accept-Ranges': 'bytes',
                        'Content-Length': str(content_length),
                        'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET',
                        'Access-Control-Allow-Headers': 'Content-Type, Range',
                        'Cache-Control': 'no-cache'
                    }
                )
                return response
            else:
                logger.info("普通文件请求")
                # 普通请求
                if filename.endswith('.avi'):
                    mimetype = 'video/x-msvideo'
                elif filename.endswith('.mp4'):
                    mimetype = 'video/mp4'
                elif filename.endswith('.webm'):
                    mimetype = 'video/webm'
                else:
                    mimetype = 'video/mp4'
                
                response = send_from_directory(
                    outputs_path, 
                    filename, 
                    mimetype=mimetype,
                    as_attachment=False
                )
                response.headers['Accept-Ranges'] = 'bytes'
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range'
                response.headers['Cache-Control'] = 'no-cache'
                
                logger.info("返回普通文件响应")
                return response
            
        except Exception as e:
            logger.error(f"提供文件失败: {str(e)}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return jsonify({'error': '文件服务异常', 'details': str(e)}), 500
    
    # ========================= WebSocket 事件 =========================
    
    @socketio.on('connect', namespace='/detection')
    def handle_connect():
        """WebSocket连接事件"""
        client_id = str(uuid.uuid4())
        websocket_clients[request.sid] = client_id
        emit('connected', {'client_id': client_id})
        logger.info(f"WebSocket客户端连接: {client_id}")
    
    @socketio.on('disconnect', namespace='/detection')
    def handle_disconnect():
        """WebSocket断开事件"""
        client_id = websocket_clients.pop(request.sid, None)
        logger.info(f"WebSocket客户端断开: {client_id}")
    
    @socketio.on('join_task', namespace='/detection')
    def handle_join_task(data):
        """加入任务房间"""
        task_id = data.get('task_id')
        if task_id:
            join_room(f"task_{task_id}")
            emit('joined_task', {'task_id': task_id})
    
    @socketio.on('leave_task', namespace='/detection')
    def handle_leave_task(data):
        """离开任务房间"""
        task_id = data.get('task_id')
        if task_id:
            leave_room(f"task_{task_id}")
            emit('left_task', {'task_id': task_id})
    
    # ========================= 错误处理 =========================
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '请求的资源不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': '服务器内部错误'}), 500
    
    # ========================= 返回应用实例 =========================
    
    app.socketio = socketio
    return app


if __name__ == '__main__':
    # 创建应用实例
    app = create_app('development')
    
    # 启动应用
    print("=" * 50)
    print("智能行为检测系统 - 后端服务")
    print("=" * 50)
    print(f"服务地址: http://localhost:5000")
    print(f"API文档: http://localhost:5000/api/health")
    print("=" * 50)
    
    app.socketio.run(app, 
                    host='0.0.0.0', 
                    port=5000, 
                    debug=True, 
                    use_reloader=False)