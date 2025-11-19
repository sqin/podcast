"""单独测试RSS下载功能"""
import sys
import os
from src.utils import setup_logging, load_config
from src.rss_parser import RSSParser


def main():
    import argparse
    
    parser_cmd = argparse.ArgumentParser(description='RSS下载功能测试')
    parser_cmd.add_argument('-n', '--count', type=int, default=1, help='要下载的episode数量（默认: 1）')
    args = parser_cmd.parse_args()
    
    print("=" * 60)
    print("RSS下载功能测试")
    print("=" * 60)
    
    # 设置日志
    config = load_config()
    setup_logging(
        log_level=config.get('logging', {}).get('level', 'INFO'),
        log_file=config.get('logging', {}).get('file')
    )
    
    parser = RSSParser(
        feed_url=config['rss']['feed_url'],
        download_dir=config['paths']['raw_audio'],
        record_file=config['paths'].get('download_record', 'data/downloaded_episodes.json')
    )
    
    # 显示已下载记录
    downloaded_count = len(parser.downloaded_episodes)
    print(f"\n已下载记录: {downloaded_count} 个episode")
    
    # 下载指定数量的新episode
    print(f"\n正在下载 {args.count} 个新episode...")
    episodes = parser.download_episodes(count=args.count)
    
    if episodes:
        print(f"\n✓ 成功下载 {len(episodes)} 个episode:")
        for i, episode_data in enumerate(episodes, 1):
            print(f"\n  Episode {i}:")
            print(f"    标题: {episode_data['title']}")
            print(f"    发布日期: {episode_data['pub_date']}")
            print(f"    MP3路径: {episode_data['mp3_path']}")
            if os.path.exists(episode_data['mp3_path']):
                size_mb = os.path.getsize(episode_data['mp3_path']) / 1024 / 1024
                print(f"    文件大小: {size_mb:.2f} MB")
    else:
        print("\n✗ 没有下载到新episode")
        print("  可能原因: 所有episode都已下载，或RSS feed中没有episode")
        
        # 显示最新episode信息
        latest = parser.get_latest_episode()
        if latest:
            print(f"\n最新episode信息:")
            print(f"  标题: {latest.get('title', 'Unknown')}")
            print(f"  发布日期: {latest.get('published', 'Unknown')}")
            if parser.is_episode_downloaded(latest):
                print(f"  状态: 已下载")
            else:
                print(f"  状态: 未下载")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

