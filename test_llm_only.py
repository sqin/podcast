"""单独测试大模型处理功能"""
import sys
from pathlib import Path
from src.utils import setup_logging, load_config
from src.llm_processor import LLMProcessor


def main():
    print("=" * 60)
    print("大模型处理功能测试")
    print("=" * 60)
    
    # 设置日志
    config = load_config()
    setup_logging(
        log_level=config.get('logging', {}).get('level', 'INFO'),
        log_file=config.get('logging', {}).get('file')
    )
    
    processor = LLMProcessor(
        api_key=config['llm']['api_key'],
        model=config['llm']['model']
    )
    
    # 查找SRT文件
    srt_dir = Path(config['paths']['srt_output'])
    srt_files = list(srt_dir.glob("*.srt"))
    
    # 查找TXT文件
    txt_dir = Path(config['paths']['txt_output'])
    txt_files = list(txt_dir.glob("*.txt"))
    
    # 测试广告识别
    if srt_files:
        print("\n" + "-" * 60)
        print("1. 测试广告识别...")
        print("-" * 60)
        srt_path = str(srt_files[0])
        print(f"使用SRT文件: {srt_path}")
        
        try:
            ad_segments = processor.detect_ads(srt_path)
            
            if ad_segments:
                print(f"\n✓ 识别到 {len(ad_segments)} 个广告片段:")
                for i, (start, end) in enumerate(ad_segments, 1):
                    duration = end - start
                    print(f"  片段 {i}: {start:.2f}秒 - {end:.2f}秒 (时长: {duration:.2f}秒)")
            else:
                print("\n✓ 未识别到广告片段")
                
        except Exception as e:
            print(f"\n✗ 广告识别失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n✗ 未找到SRT文件")
        print(f"  请先运行: python test_whisper_only.py")
    
    # 测试内容处理
    if txt_files:
        print("\n" + "-" * 60)
        print("2. 测试内容处理（翻译和格式化）...")
        print("-" * 60)
        txt_path = str(txt_files[0])
        print(f"使用TXT文件: {txt_path}")
        print("这可能需要一些时间，请耐心等待...")
        
        try:
            processed_content = processor.process_transcript(txt_path)
            
            # 保存处理后的内容
            output_dir = Path(config['paths']['outputs'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"{Path(txt_path).stem}_processed.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            print(f"\n✓ 内容处理完成")
            print(f"  输出文件: {output_file}")
            print(f"  文件大小: {output_file.stat().st_size / 1024:.2f} KB")
            
            # 显示预览
            preview_lines = processed_content.split('\n')[:10]
            print(f"\n  内容预览（前10行）:")
            print("  " + "-" * 50)
            for line in preview_lines:
                if line.strip():
                    print(f"  {line}")
            print("  " + "-" * 50)
            
        except Exception as e:
            print(f"\n✗ 内容处理失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n✗ 未找到TXT文件")
        print(f"  请先运行: python test_whisper_only.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()

