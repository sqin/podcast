"""单独测试RSS下载功能"""
import sys
import os
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser
from src.utils import setup_logging, load_config, sanitize_filename
from src.rss_parser import RSSParser


def download_all_episodes(parser, output_dir, resume=False):
    """下载所有episode到指定目录，每100集一个子目录
    
    Args:
        parser: RSSParser实例
        output_dir: 输出目录
        resume: 是否断点续传（跳过已存在的文件）
    """
    print("\n" + "=" * 60)
    if resume:
        print("断点续传：继续下载所有episode")
    else:
        print("批量下载所有episode")
    print("=" * 60)
    print(f"输出目录: {output_dir}")
    print("目录结构: 每100集一个子目录 (1-100, 101-200, ...)")
    print("=" * 60)
    
    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 获取所有episode
    print("\n正在获取所有episode...")
    all_episodes = parser.get_all_episodes()
    
    if not all_episodes:
        print("✗ 没有找到任何episode")
        return
    
    print(f"找到 {len(all_episodes)} 个episode")
    
    # 按发布时间排序（从最老的开始）
    print("\n正在按发布时间排序（从最老到最新）...")
    def get_pub_date(episode):
        """获取episode的发布时间"""
        pub_date_str = episode.get('published', '')
        if not pub_date_str:
            return datetime.min
        try:
            return date_parser.parse(pub_date_str)
        except:
            return datetime.min
    
    sorted_episodes = sorted(all_episodes, key=get_pub_date)
    print(f"排序完成，最早: {sorted_episodes[0].get('published', 'Unknown')}")
    print(f"最晚: {sorted_episodes[-1].get('published', 'Unknown')}")
    
    # 统计已存在的文件（断点续传）
    if resume:
        print("\n正在检查已存在的文件...")
        existing_count = 0
        for index, episode in enumerate(sorted_episodes, 1):
            subdir_index = ((index - 1) // 100) + 1
            start_num = (subdir_index - 1) * 100 + 1
            end_num = subdir_index * 100
            subdir_name = f"{start_num}-{end_num}"
            subdir_path = output_path / subdir_name
            
            title = episode.get('title', 'Unknown')
            safe_title = sanitize_filename(title)
            filename = f"{safe_title}.mp3"
            filepath = subdir_path / filename
            
            if filepath.exists():
                existing_count += 1
        print(f"已找到 {existing_count} 个已存在的文件，将跳过")
    
    # 开始下载
    print("\n开始下载...")
    downloaded_count = 0
    skipped_count = 0
    error_count = 0
    retry_count = 0
    
    for index, episode in enumerate(sorted_episodes, 1):
        # 计算子目录名称（每100集一个目录）
        subdir_index = ((index - 1) // 100) + 1
        start_num = (subdir_index - 1) * 100 + 1
        end_num = subdir_index * 100
        subdir_name = f"{start_num}-{end_num}"
        subdir_path = output_path / subdir_name
        subdir_path.mkdir(parents=True, exist_ok=True)
        
        title = episode.get('title', 'Unknown')
        pub_date = episode.get('published', 'Unknown')
        
        print(f"\n[{index}/{len(sorted_episodes)}] {title}")
        print(f"  目录: {subdir_name}/")
        print(f"  发布日期: {pub_date}")
        
        # 生成文件名
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}.mp3"
        filepath = subdir_path / filename
        
        # 检查文件是否已存在（断点续传）
        if filepath.exists():
            file_size = filepath.stat().st_size
            size_mb = file_size / 1024 / 1024
            
            # 检查文件大小是否合理（MP3文件通常至少几十KB）
            if file_size < 10240:  # 小于10KB可能是损坏或不完整的文件
                print(f"  ⚠ 文件存在但可能不完整 ({size_mb:.2f} MB < 10KB)，将重新下载")
                try:
                    filepath.unlink()  # 删除不完整的文件
                except:
                    pass
            else:
                print(f"  ✓ 文件已存在 ({size_mb:.2f} MB)，跳过")
                skipped_count += 1
                continue
        
        # 获取MP3 URL
        mp3_url = parser.get_mp3_url(episode)
        if not mp3_url:
            print(f"  ✗ 无法获取MP3 URL")
            error_count += 1
            continue
        
        # 下载MP3（带重试机制和超时处理）
        max_retries = 3
        retry = 0
        success = False
        timeout_seconds = 60  # 1分钟超时
        
        while retry < max_retries and not success:
            try:
                if retry > 0:
                    print(f"  ↻ 重试下载 ({retry}/{max_retries-1})...")
                    retry_count += 1
                
                # 显示下载进度和速度，设置超时时间
                downloaded_path = parser.download_mp3(
                    mp3_url, 
                    filename, 
                    target_dir=str(subdir_path), 
                    show_progress=True,
                    timeout=timeout_seconds
                )
                if downloaded_path and Path(downloaded_path).exists():
                    file_size = Path(downloaded_path).stat().st_size
                    size_mb = file_size / 1024 / 1024
                    
                    # 再次检查文件大小
                    if file_size < 10240:
                        print(f"  ⚠ 下载的文件可能不完整 ({size_mb:.2f} MB < 10KB)，将重试")
                        try:
                            Path(downloaded_path).unlink()
                        except:
                            pass
                        retry += 1
                        continue
                    
                    print(f"  ✓ 下载完成 ({size_mb:.2f} MB)")
                    downloaded_count += 1
                    success = True
                else:
                    print(f"  ✗ 下载失败：文件不存在")
                    retry += 1
            except TimeoutError as e:
                print(f"  ⏱ 下载超时: {e}")
                print(f"  ⏭ 跳过此文件，继续下载下一个")
                error_count += 1
                break  # 超时不重试，直接跳过
            except Exception as e:
                print(f"  ✗ 下载失败: {e}")
                retry += 1
                if retry < max_retries:
                    import time
                    time.sleep(2)  # 等待2秒后重试
        
        if not success:
            error_count += 1
        
        # 每10个episode显示一次进度
        if index % 10 == 0:
            print(f"\n进度: {index}/{len(sorted_episodes)} (已下载: {downloaded_count}, 跳过: {skipped_count}, 错误: {error_count}, 重试: {retry_count})")
    
    # 总结
    print("\n" + "=" * 60)
    print("下载完成")
    print("=" * 60)
    print(f"总计: {len(sorted_episodes)} 个episode")
    print(f"成功下载: {downloaded_count} 个")
    print(f"跳过（已存在）: {skipped_count} 个")
    print(f"错误: {error_count} 个")
    if retry_count > 0:
        print(f"重试次数: {retry_count} 次")
    print(f"输出目录: {output_dir}")


def main():
    import argparse
    
    parser_cmd = argparse.ArgumentParser(description='RSS下载功能测试')
    parser_cmd.add_argument('-n', '--count', type=int, default=1, help='要下载的episode数量（默认: 1）')
    parser_cmd.add_argument('--all', action='store_true', help='下载所有episode')
    parser_cmd.add_argument('--resume', action='store_true', help='断点续传：继续下载所有episode（跳过已存在的文件）')
    parser_cmd.add_argument('--output-dir', type=str, default=None, help='批量下载时的输出目录（仅在使用--all或--resume时有效）')
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
    
    # 批量下载模式或断点续传模式
    if args.all or args.resume:
        output_dir = args.output_dir
        if not output_dir:
            output_dir = "data/all_episodes"
            print(f"\n未指定输出目录，使用默认目录: {output_dir}")
        download_all_episodes(parser, output_dir, resume=args.resume or args.all)
        return
    
    # 正常下载模式
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

