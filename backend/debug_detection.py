#!/usr/bin/env python3
"""
调试检测流程，逐步定位异常
"""
import os
import sys
import cv2
import time
import traceback

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
yolo_slowfast_path = os.path.join(project_root, 'yolo_slowfast-master')
sys.path.append(yolo_slowfast_path)

print(f"当前目录: {current_dir}")
print(f"项目根目录: {project_root}")
print(f"算法目录: {yolo_slowfast_path}")

def test_basic_opencv():
    """测试基本OpenCV功能"""
    print("\n=== 测试基本OpenCV功能 ===")
    try:
        video_path = "uploads/1751168979_cf2eb096f9d83d6135525d40dfba9b82.mp4"
        if not os.path.exists(video_path):
            print(f"❌ 视频文件不存在: {video_path}")
            return False
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("❌ 无法打开视频")
            return False
        
        print("✓ 视频打开成功")
        
        # 测试读取帧
        for i in range(5):
            ret, frame = cap.read()
            if not ret:
                print(f"❌ 读取第{i+1}帧失败")
                break
            print(f"✓ 成功读取第{i+1}帧: {frame.shape}")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ OpenCV测试失败: {e}")
        print(f"异常详情: {traceback.format_exc()}")
        return False

def test_yolo_import():
    """测试YOLO导入"""
    print("\n=== 测试YOLO导入 ===")
    try:
        from ultralytics import YOLO
        print("✓ YOLO导入成功")
        
        model = YOLO('yolov8n.pt')
        print("✓ YOLO模型加载成功")
        return True
        
    except Exception as e:
        print(f"❌ YOLO测试失败: {e}")
        print(f"异常详情: {traceback.format_exc()}")
        return False

def test_algorithm_import():
    """测试算法模块导入"""
    print("\n=== 测试算法模块导入 ===")
    try:
        # 切换到算法目录
        original_cwd = os.getcwd()
        os.chdir(yolo_slowfast_path)
        print(f"切换到算法目录: {os.getcwd()}")
        
        # 测试导入
        from yolo_slowfast import MyVideoCapture
        print("✓ MyVideoCapture导入成功")
        
        # 恢复目录
        os.chdir(original_cwd)
        return True
        
    except Exception as e:
        print(f"❌ 算法模块导入失败: {e}")
        print(f"异常详情: {traceback.format_exc()}")
        # 恢复目录
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False

def test_video_capture():
    """测试MyVideoCapture"""
    print("\n=== 测试MyVideoCapture ===")
    try:
        # 切换到算法目录
        original_cwd = os.getcwd()
        os.chdir(yolo_slowfast_path)
        
        from yolo_slowfast import MyVideoCapture
        
        video_path = os.path.join(original_cwd, "uploads/1751168979_cf2eb096f9d83d6135525d40dfba9b82.mp4")
        print(f"视频路径: {video_path}")
        
        cap = MyVideoCapture(video_path)
        print("✓ MyVideoCapture创建成功")
        
        # 测试读取
        for i in range(3):
            ret, frame = cap.read()
            if ret:
                print(f"✓ 成功读取帧 {i+1}: {frame.shape}")
            else:
                print(f"❌ 读取帧 {i+1} 失败")
                break
        
        cap.release()
        os.chdir(original_cwd)
        return True
        
    except Exception as e:
        print(f"❌ MyVideoCapture测试失败: {e}")
        print(f"异常详情: {traceback.format_exc()}")
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False

def test_video_writer():
    """测试视频写入"""
    print("\n=== 测试视频写入 ===")
    try:
        # 测试参数
        output_path = "test_output.mp4"
        width, height = 640, 480
        fps = 25
        
        # 测试编解码器
        codecs_to_test = [
            ('avc1', 'H.264 (最佳)'),
            ('mp4v', 'MPEG-4'),
            ('XVID', 'XVID')
        ]
        
        for codec, desc in codecs_to_test:
            try:
                print(f"测试编解码器: {codec} - {desc}")
                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                
                if writer.isOpened():
                    # 写入几帧测试
                    import numpy as np
                    for i in range(3):
                        frame = np.zeros((height, width, 3), dtype=np.uint8)
                        frame[:, :, i%3] = 255  # RGB轮换
                        success = writer.write(frame)
                        if not success:
                            print(f"  ❌ 写入帧 {i+1} 失败")
                            break
                        else:
                            print(f"  ✓ 写入帧 {i+1} 成功")
                    
                    writer.release()
                    
                    # 检查文件
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"  ✓ {codec} 编解码器可用，文件大小: {os.path.getsize(output_path)} bytes")
                        os.remove(output_path)
                        return True
                    else:
                        print(f"  ❌ {codec} 编解码器生成文件无效")
                else:
                    print(f"  ❌ {codec} 编解码器无法打开")
                    
            except Exception as e:
                print(f"  ❌ {codec} 编解码器测试异常: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 视频写入测试失败: {e}")
        print(f"异常详情: {traceback.format_exc()}")
        return False

def main():
    print("开始调试检测流程...")
    print("=" * 50)
    
    tests = [
        ("基本OpenCV", test_basic_opencv),
        ("YOLO导入", test_yolo_import),
        ("算法模块导入", test_algorithm_import),
        ("MyVideoCapture", test_video_capture),
        ("视频写入", test_video_writer)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for test_name, result in results.items():
        status = "✓ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    failed_tests = [name for name, result in results.items() if not result]
    if failed_tests:
        print(f"\n失败的测试: {', '.join(failed_tests)}")
    else:
        print("\n所有测试通过！")

if __name__ == "__main__":
    main() 