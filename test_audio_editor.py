"""单独测试音频编辑功能（去除广告）"""
import sys
import os
from pathlib import Path
from src.utils import setup_logging, load_config
from src.audio_editor import AudioEditor
from src.llm_processor import LLMProcessor


def main():
    print("=" * 60)
    print("音频编辑功能测试 - 去除广告")
    print("=" * 60)
    
    # 设置日志
    config = load_config()
    setup_logging(
        log_level=config.get('logging', {}).get('level', 'INFO'),
        log_file=config.get('logging', {}).get('file')
    )
    
    # 查找MP3文件
    raw_audio_dir = Path(config['paths']['raw_audio'])
    mp3_files = list(raw_audio_dir.glob("*.mp3"))
    
    if not mp3_files:
        print("\n✗ 未找到MP3文件")
        print(f"  请先下载MP3文件到: {raw_audio_dir}")
        print("  或运行: python test_rss_only.py")
        return
    
    # 使用最新的MP3文件
    mp3_path = str(mp3_files[0])
    print(f"\n使用MP3文件: {mp3_path}")
    
    # 查找对应的SRT文件
    srt_dir = Path(config['paths']['srt_output'])
    mp3_name = Path(mp3_path).stem
    srt_files = list(srt_dir.glob(f"{mp3_name}.srt"))
    
    if not srt_files:
        print("\n✗ 未找到对应的SRT文件")
        print(f"  请先生成SRT文件: {srt_dir}")
        print("  或运行: python test_whisper_only.py")
        return
    
    srt_path = str(srt_files[0])
    print(f"使用SRT文件: {srt_path}")
    
    # 识别广告
    print("\n" + "-" * 60)
    print("步骤 1: 识别广告时间段")
    print("-" * 60)
    
    processor = LLMProcessor(
        api_key=config['llm']['api_key'],
        model=config['llm']['model']
    )
    
    try:
        ad_segments = processor.detect_ads(srt_path)
        
        if ad_segments:
            print(f"\n✓ 识别到 {len(ad_segments)} 个广告片段:")
            for i, (start, end) in enumerate(ad_segments, 1):
                print(f"  片段 {i}: {start:.2f}秒 - {end:.2f}秒 (时长: {end-start:.2f}秒)")
        else:
            print("\n✓ 未识别到广告片段")
            print("  无法进行去除广告操作")
            return
            
    except Exception as e:
        print(f"\n✗ 广告识别失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 去除广告
    print("\n" + "-" * 60)
    print("步骤 2: 去除广告片段")
    print("-" * 60)
    
    try:
        editor = AudioEditor()
        
        # 获取原始文件信息
        original_size = os.path.getsize(mp3_path) / 1024 / 1024
        duration = editor.get_audio_duration(mp3_path)
        print(f"\n原始音频信息:")
        print(f"  文件大小: {original_size:.2f} MB")
        print(f"  时长: {duration:.2f} 秒 ({duration/60:.2f} 分钟)")
        
        # 去除广告
        print(f"\n开始去除广告...")
        processed_mp3_path = editor.remove_ads(
            input_path=mp3_path,
            ad_segments=ad_segments,
            output_dir=config['paths']['processed_audio']
        )
        
        print(f"\n✓ 去除广告完成: {processed_mp3_path}")
        
        # 显示处理后的文件信息
        processed_size = os.path.getsize(processed_mp3_path) / 1024 / 1024
        processed_duration = editor.get_audio_duration(processed_mp3_path)
        
        print(f"\n处理后音频信息:")
        print(f"  文件大小: {processed_size:.2f} MB")
        print(f"  时长: {processed_duration:.2f} 秒 ({processed_duration/60:.2f} 分钟)")
        
        # 计算减少量
        size_reduction = original_size - processed_size
        duration_reduction = duration - processed_duration
        size_percent = (size_reduction / original_size * 100) if original_size > 0 else 0
        duration_percent = (duration_reduction / duration * 100) if duration > 0 else 0
        
        print(f"\n减少量:")
        print(f"  文件大小: {size_reduction:.2f} MB ({size_percent:.1f}%)")
        print(f"  时长: {duration_reduction:.2f} 秒 ({duration_reduction/60:.2f} 分钟, {duration_percent:.1f}%)")
        
    except Exception as e:
        print(f"\n✗ 去除广告失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()

