"""单独测试Whisper生成功能"""
import sys
from pathlib import Path
from src.utils import setup_logging, load_config
from src.whisper_processor import WhisperProcessor


def main():
    print("=" * 60)
    print("Whisper生成功能测试")
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
    
    processor = WhisperProcessor(
        small_model=config['whisper']['small_model'],
        large_model=config['whisper']['large_model'],
        device=config['whisper']['device']
    )
    
    # 生成SRT
    print("\n" + "-" * 60)
    print("1. 生成SRT文件...")
    print("-" * 60)
    try:
        srt_path = processor.generate_srt(
            mp3_path,
            output_dir=config['paths']['srt_output']
        )
        print(f"✓ SRT文件已生成: {srt_path}")
    except Exception as e:
        print(f"✗ SRT生成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 生成TXT
    print("\n" + "-" * 60)
    print("2. 生成TXT文件...")
    print("-" * 60)
    try:
        txt_path = processor.generate_txt(
            mp3_path,
            output_dir=config['paths']['txt_output']
        )
        print(f"✓ TXT文件已生成: {txt_path}")
        
        # 显示文件大小
        txt_size = Path(txt_path).stat().st_size
        print(f"  文件大小: {txt_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"✗ TXT生成失败: {e}")
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

