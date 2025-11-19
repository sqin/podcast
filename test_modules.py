"""测试前三个模块的脚本"""
import sys
from src.utils import setup_logging, load_config
from src.rss_parser import RSSParser
from src.whisper_processor import WhisperProcessor


def test_rss_parser():
    """测试RSS解析模块"""
    print("=" * 50)
    print("测试RSS解析模块")
    print("=" * 50)
    
    config = load_config()
    parser = RSSParser(
        feed_url=config['rss']['feed_url'],
        download_dir=config['paths']['raw_audio']
    )
    
    # 检查今天的新episode
    episode_data = parser.process_today_episode()
    
    if episode_data:
        print(f"\n✓ 找到今天的新episode:")
        print(f"  标题: {episode_data['title']}")
        print(f"  发布日期: {episode_data['pub_date']}")
        print(f"  MP3路径: {episode_data['mp3_path']}")
        return episode_data
    else:
        print("\n✗ 今天没有新episode")
        return None


def test_whisper_processor(mp3_path):
    """测试Whisper处理模块"""
    if not mp3_path:
        print("\n跳过Whisper测试（没有MP3文件）")
        return
    
    print("\n" + "=" * 50)
    print("测试Whisper处理模块")
    print("=" * 50)
    
    config = load_config()
    processor = WhisperProcessor(
        small_model=config['whisper']['small_model'],
        large_model=config['whisper']['large_model'],
        device=config['whisper']['device']
    )
    
    # 生成SRT文件
    print("\n1. 生成SRT文件（使用small模型）...")
    try:
        srt_path = processor.generate_srt(
            mp3_path,
            output_dir=config['paths']['srt_output']
        )
        print(f"   ✓ SRT文件已生成: {srt_path}")
    except Exception as e:
        print(f"   ✗ SRT生成失败: {e}")
        return
    
    # 生成TXT文件
    print("\n2. 生成TXT文件（使用large-v3模型）...")
    try:
        txt_path = processor.generate_txt(
            mp3_path,
            output_dir=config['paths']['txt_output']
        )
        print(f"   ✓ TXT文件已生成: {txt_path}")
    except Exception as e:
        print(f"   ✗ TXT生成失败: {e}")


if __name__ == "__main__":
    # 设置日志
    config = load_config()
    setup_logging(
        log_level=config.get('logging', {}).get('level', 'INFO'),
        log_file=config.get('logging', {}).get('file')
    )
    
    # 测试RSS解析
    episode_data = test_rss_parser()
    
    # 测试Whisper处理（如果有episode）
    if episode_data:
        test_whisper_processor(episode_data['mp3_path'])
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

