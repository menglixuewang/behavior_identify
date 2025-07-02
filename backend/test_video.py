#!/usr/bin/env python3
"""
测试OpenCV视频处理功能
"""
import cv2
import os
import traceback

def test_video_read(video_path):
    """测试视频读取功能"""
    print(f"测试视频文件: {video_path}")
    
    if not os.path.exists(video_path):
        print("❌ 视频文件不存在")
        return False
    
    try:
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("❌ 无法打开视频文件")
            return False
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        
        print(f"✓ 视频信息:")
        print(f"  - 分辨率: {width}x{height}")
        print(f"  - 帧率: {fps}")
        print(f"  - 总帧数: {frame_count}")
        print(f"  - 编解码器: {fourcc}")
        
        # 尝试读取前几帧
        frame_read_count = 0
        for i in range(min(10, frame_count)):
            ret, frame = cap.read()
            if ret:
                frame_read_count += 1
            else:
                print(f"❌ 读取第{i+1}帧失败")
                break
        
        print(f"✓ 成功读取前{frame_read_count}帧")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ 读取视频时发生异常: {str(e)}")
        print(f"异常详情:\n{traceback.format_exc()}")
        return False

def test_video_write():
    """测试视频写入功能"""
    print("\n测试视频写入功能...")
    
    try:
        # 创建测试视频
        output_path = "test_output.mp4"
        width, height = 640, 480
        fps = 30
        
        # 测试不同的编解码器
        codecs_to_test = [
            ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),
            ('avc1', cv2.VideoWriter_fourcc(*'avc1')),
            ('H264', cv2.VideoWriter_fourcc('H', '2', '6', '4')),
            ('MJPG', cv2.VideoWriter_fourcc(*'MJPG'))
        ]
        
        for codec_name, fourcc in codecs_to_test:
            print(f"测试编解码器: {codec_name}")
            
            try:
                writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                
                if writer.isOpened():
                    # 写入几帧测试
                    import numpy as np
                    for i in range(5):
                        frame = np.zeros((height, width, 3), dtype=np.uint8)
                        frame[:, :, 0] = i * 50  # 变化的红色
                        writer.write(frame)
                    
                    writer.release()
                    
                    # 验证文件是否生成
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✓ {codec_name} 编解码器可用")
                        os.remove(output_path)
                        return True
                    else:
                        print(f"❌ {codec_name} 编解码器生成的文件无效")
                else:
                    print(f"❌ {codec_name} 编解码器不可用")
                    
            except Exception as e:
                print(f"❌ {codec_name} 编解码器测试失败: {str(e)}")
        
        return False
        
    except Exception as e:
        print(f"❌ 视频写入测试异常: {str(e)}")
        print(f"异常详情:\n{traceback.format_exc()}")
        return False

def main():
    print("OpenCV 视频处理测试")
    print("=" * 40)
    
    # 测试现有视频文件
    video_files = [
        "uploads/1751168979_cf2eb096f9d83d6135525d40dfba9b82.mp4",
        "uploads/1751161726_fall.mp4"
    ]
    
    for video_file in video_files:
        if os.path.exists(video_file):
            test_video_read(video_file)
            break
    
    # 测试视频写入
    test_video_write()
    
    print("\n测试完成")

if __name__ == "__main__":
    main() 