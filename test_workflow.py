"""测试完整工作流：RSS下载、Whisper生成、大模型处理"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from src.utils import setup_logging, load_config
from src.rss_parser import RSSParser
from src.whisper_processor import WhisperProcessor
from src.llm_processor import LLMProcessor
from src.audio_editor import AudioEditor
from src.text_editor import TextEditor


class ProcessRecordManager:
    """处理记录管理器"""
    
    def __init__(self, record_file="data/processed_episodes.json"):
        self.record_file = Path(record_file)
        self.processed_episodes = self._load_records()
    
    def _load_records(self):
        """加载处理记录"""
        if not self.record_file.exists():
            return {}
        
        try:
            with open(self.record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            return records
        except Exception as e:
            print(f"⚠ 加载处理记录失败: {e}，将创建新记录")
            return {}
    
    def _save_records(self):
        """保存处理记录"""
        try:
            self.record_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.record_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_episodes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠ 保存处理记录失败: {e}")
    
    def _get_episode_id(self, episode):
        """获取episode的唯一标识符（与RSSParser保持一致）"""
        # 优先使用guid，如果没有则使用link
        guid = episode.get('id') or episode.get('guid', '')
        if guid:
            return str(guid)
        
        link = episode.get('link', '')
        if link:
            return link
        
        # 如果都没有，使用title和pubDate组合
        title = episode.get('title', '')
        pub_date = episode.get('published', '')
        return f"{title}_{pub_date}"
    
    def is_episode_processed(self, episode):
        """检查episode是否已处理"""
        episode_id = self._get_episode_id(episode)
        return episode_id in self.processed_episodes
    
    def record_processed_episode(self, episode, mp3_path, txt_path):
        """记录已处理的episode"""
        episode_id = self._get_episode_id(episode)
        title = episode.get('title', Path(mp3_path).stem)
        pub_date = episode.get('published', '')
        
        self.processed_episodes[episode_id] = {
            'title': title,
            'published': pub_date,
            'mp3_path': mp3_path,
            'txt_path': txt_path,
            'processed_at': datetime.now().isoformat()
        }
        self._save_records()


def test_rss_search_and_download(search_text, use_existing=True, process_record_manager=None):
    """通过标题搜索并下载episode"""
    print("\n" + "=" * 60)
    print(f"步骤 1: 搜索episode: {search_text}")
    print("=" * 60)
    
    config = load_config()
    parser = RSSParser(
        feed_url=config['rss']['feed_url'],
        download_dir=config['paths']['raw_audio'],
        record_file=config['paths'].get('download_record', 'data/downloaded_episodes.json')
    )
    
    # 搜索episode
    matched_episodes = parser.search_episodes(search_text)
    
    if not matched_episodes:
        print(f"\n✗ 未找到匹配的episode: {search_text}")
        return []
    
    if len(matched_episodes) > 1:
        # 多个匹配，打印列表
        print(f"\n找到 {len(matched_episodes)} 个匹配的episode:")
        print("-" * 60)
        for i, episode in enumerate(matched_episodes, 1):
            title = episode.get('title', 'Unknown')
            pub_date = episode.get('published', '')
            print(f"{i}. {title}")
            print(f"   发布日期: {pub_date}")
            print()
        print("-" * 60)
        print("请使用更精确的搜索关键词，或使用完整标题")
        return []
    
    # 只有一个匹配，直接处理
    episode = matched_episodes[0]
    title = episode.get('title', 'Unknown')
    pub_date = episode.get('published', '')
    
    print(f"\n✓ 找到匹配的episode: {title}")
    
    # 检查是否已处理
    if process_record_manager and process_record_manager.is_episode_processed(episode):
        print(f"  ✓ Episode已处理，跳过")
        return []
    
    # 检查是否已下载
    episode_data_list = []
    if parser.is_episode_downloaded(episode):
        if use_existing:
            print(f"  ✓ Episode已下载，直接使用")
            episode_id = parser._get_episode_id(episode)
            if episode_id in parser.downloaded_episodes:
                mp3_path = parser.downloaded_episodes[episode_id]['mp3_path']
                print(f"  MP3路径: {mp3_path}")
                episode_data_list.append({
                    'title': title,
                    'pub_date': pub_date,
                    'mp3_path': mp3_path,
                    'episode': episode
                })
            else:
                # 如果记录中没有路径，尝试从文件名查找
                from src.utils import sanitize_filename
                safe_title = sanitize_filename(title)
                mp3_path = Path(parser.download_dir) / f"{safe_title}.mp3"
                if mp3_path.exists():
                    print(f"  MP3路径: {mp3_path}")
                    episode_data_list.append({
                        'title': title,
                        'pub_date': pub_date,
                        'mp3_path': str(mp3_path),
                        'episode': episode
                    })
        else:
            print(f"  ⚠ Episode已下载，但use_existing=False，跳过")
    else:
        # 未下载，下载episode
        print(f"  Episode未下载，开始下载...")
        try:
            episode_data = parser._download_single_episode(episode)
            if episode_data:
                print(f"  ✓ 下载完成: {episode_data['mp3_path']}")
                episode_data_list.append(episode_data)
        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
    
    return episode_data_list


def test_rss_download(count=1, use_existing=True, process_record_manager=None):
    """获取episode列表（如果已下载则直接使用，否则下载）
    
    Args:
        count: 下载多少个最近的episode（默认1）
        use_existing: 如果episode已下载，是否使用已下载的（默认True）
    
    Returns:
        返回episode数据列表，每个元素包含title、pub_date、mp3_path、episode等信息
    """
    print("\n" + "=" * 60)
    print(f"步骤 1: 获取最近 {count} 个episode")
    print("=" * 60)
    
    config = load_config()
    parser = RSSParser(
        feed_url=config['rss']['feed_url'],
        download_dir=config['paths']['raw_audio'],
        record_file=config['paths'].get('download_record', 'data/downloaded_episodes.json')
    )
    
    # 显示已下载记录
    downloaded_count = len(parser.downloaded_episodes)
    print(f"\n已下载记录: {downloaded_count} 个episode")
    
    # 获取最近的episode列表
    print(f"\n正在获取最近 {count} 个episode...")
    episodes = parser.get_all_episodes(limit=count)
    
    if not episodes:
        print("\n✗ 未找到episode")
        return []
    
    episode_data_list = []
    
    for episode in episodes:
        title = episode.get('title', 'Unknown')
        pub_date = episode.get('published', '')
        
        # 检查是否已处理（优先检查处理记录）
        if process_record_manager and process_record_manager.is_episode_processed(episode):
            print(f"\n✓ Episode已处理，跳过: {title}")
            continue
        
        # 检查是否已下载
        if parser.is_episode_downloaded(episode):
            if use_existing:
                print(f"\n✓ Episode已下载，直接使用: {title}")
                # 从记录中获取MP3路径
                episode_id = parser._get_episode_id(episode)
                if episode_id in parser.downloaded_episodes:
                    mp3_path = parser.downloaded_episodes[episode_id]['mp3_path']
                    print(f"  MP3路径: {mp3_path}")
                    episode_data_list.append({
                        'title': title,
                        'pub_date': pub_date,
                        'mp3_path': mp3_path,
                        'episode': episode
                    })
                    continue
                else:
                    # 如果记录中没有路径，尝试从文件名查找
                    from src.utils import sanitize_filename
                    safe_title = sanitize_filename(title)
                    mp3_path = Path(parser.download_dir) / f"{safe_title}.mp3"
                    if mp3_path.exists():
                        print(f"  MP3路径: {mp3_path}")
                        episode_data_list.append({
                            'title': title,
                            'pub_date': pub_date,
                            'mp3_path': str(mp3_path),
                            'episode': episode
                        })
                        continue
            else:
                print(f"\n⚠ Episode已下载，但use_existing=False，跳过: {title}")
                continue
        else:
            # 未下载，下载episode
            print(f"\nEpisode未下载，开始下载: {title}")
            try:
                episode_data = parser._download_single_episode(episode)
                if episode_data:
                    print(f"  ✓ 下载完成: {episode_data['mp3_path']}")
                    episode_data_list.append(episode_data)
            except Exception as e:
                print(f"  ✗ 下载失败: {e}")
                continue
    
    if not episode_data_list:
        # 如果所有episode都被跳过（已处理或已下载但use_existing=False），直接返回
        print("\n所有episode都已处理或跳过，无需处理")
        return []
    
    print(f"\n✓ 共获取 {len(episode_data_list)} 个episode")
    return episode_data_list


def test_whisper_generation(mp3_path):
    """使用最小模型生成SRT文件（用于识别片头片尾）"""
    if not mp3_path:
        print("\n跳过Whisper测试（没有MP3文件）")
        return None
    
    print("\n" + "=" * 60)
    print("步骤 2: Whisper生成SRT文件（使用最小模型）")
    print("=" * 60)
    
    config = load_config()
    
    # 检查文件是否已存在
    mp3_name = Path(mp3_path).stem
    srt_path = Path(config['paths']['srt_output']) / f"{mp3_name}.srt"
    
    if srt_path.exists():
        print(f"\n✓ SRT文件已存在，跳过生成")
        print(f"  SRT文件: {srt_path}")
        return str(srt_path)
    
    # 使用最小模型（从配置中读取）
    min_model = config['whisper'].get('min_model', 'tiny')
    processor = WhisperProcessor(
        small_model=min_model,
        large_model=config['whisper']['large_model'],
        device=config['whisper']['device']
    )
    
    print(f"\n使用最小模型 {min_model} 生成SRT文件...")
    print("    这可能需要一些时间，请耐心等待...")
    try:
        srt_path = processor.generate_srt(
            mp3_path,
            output_dir=config['paths']['srt_output']
        )
        print(f"    ✓ SRT文件已生成: {srt_path}")
        
        # 显示SRT文件的前几行
        with open(srt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:10]
            print(f"\n    SRT文件预览（前10行）:")
            print("    " + "-" * 50)
            for line in lines:
                print(f"    {line.rstrip()}")
            print("    " + "-" * 50)
            
    except Exception as e:
        print(f"    ✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return srt_path


def test_llm_processing(srt_path, mp3_path=None, title=None):
    """大模型处理：识别片头片尾、去除音频"""
    if not srt_path:
        print("\n跳过大模型处理测试（没有SRT文件）")
        return None
    
    print("\n" + "=" * 60)
    print("步骤 3: 大模型处理（识别片头片尾）")
    print("=" * 60)
    
    config = load_config()
    processor = LLMProcessor(
        api_key=config['llm']['api_key'],
        model=config['llm']['model']
    )
    
    segments_to_remove = None
    
    # 识别片头片尾时间段
    if srt_path:
        print("\n3.1 识别片头片尾时间段...")
        try:
            segments_to_remove = processor.detect_ads(srt_path)
            
            if segments_to_remove:
                print(f"    ✓ 识别到 {len(segments_to_remove)} 个片头片尾片段:")
                for i, (start, end) in enumerate(segments_to_remove, 1):
                    print(f"       片段 {i}: {start:.2f}秒 - {end:.2f}秒 (时长: {end-start:.2f}秒)")
            else:
                print("    ✓ 未识别到片头片尾片段")
                
        except Exception as e:
            print(f"    ✗ 片头片尾识别失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # 步骤4: 去除片头片尾，生成新的MP3
    processed_mp3_path = None
    if mp3_path:
        # 检查处理后的MP3是否已存在
        mp3_name = Path(mp3_path).stem
        processed_mp3_check = Path(config['paths']['processed_audio']) / f"{mp3_name}_no_ads.mp3"
        
        if processed_mp3_check.exists():
            print("\n步骤 4: 去除片头片尾，生成新MP3...")
            print(f"    ✓ 处理后的MP3文件已存在，跳过处理: {processed_mp3_check}")
            processed_mp3_path = str(processed_mp3_check)
            
            # 显示文件大小对比
            original_size = os.path.getsize(mp3_path) / 1024 / 1024
            processed_size = os.path.getsize(processed_mp3_path) / 1024 / 1024
            print(f"    原始文件: {original_size:.2f} MB")
            print(f"    处理后: {processed_size:.2f} MB")
        elif segments_to_remove:
            print("\n步骤 4: 去除片头片尾，生成新MP3...")
            try:
                editor = AudioEditor()
                processed_mp3_path = editor.remove_ads(
                    input_path=mp3_path,
                    ad_segments=segments_to_remove,
                    output_dir=config['paths']['processed_audio']
                )
                print(f"    ✓ 去除片头片尾完成: {processed_mp3_path}")
                
                # 显示文件大小对比
                original_size = os.path.getsize(mp3_path) / 1024 / 1024
                processed_size = os.path.getsize(processed_mp3_path) / 1024 / 1024
                print(f"    原始文件: {original_size:.2f} MB")
                print(f"    处理后: {processed_size:.2f} MB")
                print(f"    减少: {original_size - processed_size:.2f} MB ({((original_size - processed_size) / original_size * 100):.1f}%)")
                
            except Exception as e:
                print(f"    ✗ 去除片头片尾失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\n步骤 4: 跳过去除片头片尾（未识别到片段）")
            processed_mp3_path = mp3_path  # 使用原始文件
    else:
        print("\n步骤 4: 跳过去除片头片尾（没有MP3文件）")
    
    return processed_mp3_path, segments_to_remove


def test_generate_final_txt(processed_mp3_path, srt_path, segments_to_remove, title=None):
    """使用处理后的MP3和large模型生成TXT文件"""
    if not processed_mp3_path:
        print("\n跳过生成最终TXT（没有处理后的MP3文件）")
        return None
    
    print("\n" + "=" * 60)
    print("步骤 5: 生成最终TXT文件（使用large模型）")
    print("=" * 60)
    
    config = load_config()
    
    # 检查文件是否已存在
    mp3_name = Path(processed_mp3_path).stem
    # 移除_no_ads后缀（如果有）
    if mp3_name.endswith('_no_ads'):
        mp3_name = mp3_name[:-7]
    
    txt_path = Path(config['paths']['txt_output']) / f"{mp3_name}_final.txt"
    
    if txt_path.exists():
        print(f"\n✓ 最终TXT文件已存在，跳过生成")
        print(f"  TXT文件: {txt_path}")
        return str(txt_path)
    
    # 使用large模型生成TXT
    large_model = config['whisper'].get('large_model', 'large-v3')
    processor = WhisperProcessor(
        small_model=config['whisper'].get('min_model', 'tiny'),
        large_model=large_model,
        device=config['whisper']['device']
    )
    
    print(f"\n使用large模型 {large_model} 生成TXT文件...")
    print("    这可能需要一些时间，请耐心等待...")
    try:
        # 直接生成到目标路径
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path_str = processor.generate_txt(
            processed_mp3_path,
            output_dir=str(txt_path.parent),
            output_filename=txt_path.name
        )
        print(f"    ✓ TXT文件已生成: {txt_path_str}")
        
        # 显示TXT文件的前几行
        with open(txt_path_str, 'r', encoding='utf-8') as f:
            content = f.read()
            preview = content[:500] if len(content) > 500 else content
            print(f"\n    TXT文件预览（前500字符）:")
            print("    " + "-" * 50)
            print(f"    {preview}...")
            print("    " + "-" * 50)
            
    except Exception as e:
        print(f"    ✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return str(txt_path_str)


def process_single_episode(episode_data, config, process_record_manager=None):
    """处理单个episode的完整工作流"""
    mp3_path = episode_data['mp3_path']
    title = episode_data.get('title', Path(mp3_path).stem)
    episode = episode_data.get('episode')
    
    # 再次检查是否已处理（双重保险）
    if process_record_manager and episode and process_record_manager.is_episode_processed(episode):
        print(f"\n{'='*60}")
        print(f"Episode已处理，跳过: {title}")
        print(f"{'='*60}")
        return True  # 返回True表示已处理（不需要重新处理）
    
    print(f"\n{'='*60}")
    print(f"开始处理: {title}")
    print(f"{'='*60}")
    
    # 步骤2: Whisper生成SRT（使用最小模型）
    srt_path = test_whisper_generation(mp3_path)
    
    if not srt_path:
        print(f"\n✗ Whisper生成失败，跳过此episode")
        return False
    
    # 步骤3-4: 大模型处理（识别片头片尾、去除音频）
    processed_mp3_path, segments_to_remove = test_llm_processing(
        srt_path, mp3_path=mp3_path, title=title
    )
    
    if not processed_mp3_path:
        print(f"\n✗ 音频处理失败，跳过此episode")
        return False
    
    # 步骤5: 使用处理后的MP3生成最终TXT文件
    final_txt_path = test_generate_final_txt(
        processed_mp3_path, srt_path, segments_to_remove, title=title
    )
    
    if not final_txt_path:
        print(f"\n✗ TXT生成失败，跳过此episode")
        return False
    
    # 步骤6: 将最终文件移到完成处理目录
    print("\n" + "=" * 60)
    print("步骤 6: 移动到完成处理目录")
    print("=" * 60)
    
    completed_dir = Path(config['paths'].get('completed', 'data/completed'))
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成最终文件名（使用episode标题）
    episode_name = Path(mp3_path).stem
    final_mp3_name = f"{episode_name}_final.mp3"
    final_txt_name = f"{episode_name}_final.txt"
    
    final_mp3_path = completed_dir / final_mp3_name
    final_txt_path_completed = completed_dir / final_txt_name
    
    # 移动文件到完成目录
    import shutil
    shutil.move(processed_mp3_path, final_mp3_path)
    shutil.move(final_txt_path, final_txt_path_completed)
    
    print(f"    ✓ MP3已移动到: {final_mp3_path}")
    print(f"    ✓ TXT已移动到: {final_txt_path_completed}")
    
    # 记录处理完成
    if process_record_manager and episode:
        process_record_manager.record_processed_episode(
            episode, str(final_mp3_path), str(final_txt_path_completed)
        )
        print(f"    ✓ 已记录处理完成")
    
    # 步骤7: 清理中间文件
    print("\n" + "=" * 60)
    print("步骤 7: 清理中间文件")
    print("=" * 60)
    
    try:
        # 删除SRT文件（不再需要）
        if srt_path and Path(srt_path).exists():
            Path(srt_path).unlink()
            print(f"    ✓ 已删除SRT文件: {srt_path}")
        
        # 删除处理后的音频目录中的临时文件（如果存在）
        processed_audio_dir = Path(config['paths']['processed_audio'])
        if processed_audio_dir.exists():
            for file in processed_audio_dir.glob("*_no_ads.mp3"):
                if file.exists():
                    file.unlink()
                    print(f"    ✓ 已删除临时MP3文件: {file}")
        
        # 删除txt_output目录中的临时文件
        txt_output_dir = Path(config['paths']['txt_output'])
        if txt_output_dir.exists():
            for file in txt_output_dir.glob("*_final.txt"):
                if file.exists() and str(file) != str(final_txt_path_completed):
                    file.unlink()
                    print(f"    ✓ 已删除临时TXT文件: {file}")
        
        print("    ✓ 中间文件清理完成")
    except Exception as e:
        print(f"    ⚠ 清理中间文件时出错: {e}")
    
    return True


def main():
    """主测试函数"""
    import argparse
    
    parser_cmd = argparse.ArgumentParser(description='播客工作流测试脚本')
    parser_cmd.add_argument(
        '--count',
        type=int,
        default=1,
        help='下载多少个最近的episode（默认: 1）'
    )
    parser_cmd.add_argument(
        '--no-use-existing',
        action='store_true',
        help='如果episode已下载，不使用已下载的，而是跳过（默认: 使用已下载的）'
    )
    parser_cmd.add_argument(
        '--search',
        type=str,
        default=None,
        help='通过标题搜索episode（使用字符串包含匹配）'
    )
    
    args = parser_cmd.parse_args()
    
    count = args.count
    use_existing = not args.no_use_existing
    search_text = args.search
    
    print("=" * 60)
    print("播客工作流测试脚本")
    print("=" * 60)
    print(f"\n参数设置:")
    if search_text:
        print(f"  - 搜索模式: {search_text}")
    else:
        print(f"  - 处理数量: {count} 个episode")
    print(f"  - 使用已下载: {'是' if use_existing else '否'}")
    print("\n本脚本将执行以下工作流：")
    print("  1. RSS下载MP3（如果已下载则跳过）")
    print("  2. Whisper使用最小模型生成SRT文件（用于识别片头片尾）")
    print("  3. 大模型识别片头片尾时间段")
    print("  4. 根据时间戳去除片头片尾，生成新MP3")
    print("  5. 使用处理后的MP3和large模型生成最终TXT文件")
    print("  6. 将最终MP3和TXT移到完成处理目录")
    print("  7. 清理中间文件")
    print("\n" + "=" * 60)
    
    # 设置日志
    config = load_config()
    log_file = config.get('logging', {}).get('file')
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    setup_logging(
        log_level=config.get('logging', {}).get('level', 'INFO'),
        log_file=log_file
    )
    
    # 初始化处理记录管理器
    processed_record_file = config['paths'].get('processed_record', 'data/processed_episodes.json')
    process_record_manager = ProcessRecordManager(record_file=processed_record_file)
    processed_count = len(process_record_manager.processed_episodes)
    print(f"已处理记录: {processed_count} 个episode")
    
    # 步骤1: 获取episode列表（搜索模式或正常模式）
    if search_text:
        # 搜索模式
        episode_data_list = test_rss_search_and_download(
            search_text=search_text,
            use_existing=use_existing,
            process_record_manager=process_record_manager
        )
    else:
        # 正常模式：获取最近的N个episode
        episode_data_list = test_rss_download(
            count=count, 
            use_existing=use_existing,
            process_record_manager=process_record_manager
        )
    
    if not episode_data_list:
        print("\n没有可用的episode，测试结束")
        return
    
    # 处理每个episode
    success_count = 0
    failed_count = 0
    
    for i, episode_data in enumerate(episode_data_list, 1):
        print(f"\n\n{'#'*60}")
        print(f"处理进度: {i}/{len(episode_data_list)}")
        print(f"{'#'*60}")
        
        try:
            if process_single_episode(episode_data, config, process_record_manager):
                success_count += 1
                print(f"\n✓ Episode处理成功: {episode_data.get('title', 'Unknown')}")
            else:
                failed_count += 1
                print(f"\n✗ Episode处理失败: {episode_data.get('title', 'Unknown')}")
        except Exception as e:
            failed_count += 1
            print(f"\n✗ Episode处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 60)
    print("工作流完成！")
    print("=" * 60)
    print(f"\n处理结果:")
    print(f"  - 成功: {success_count} 个")
    print(f"  - 失败: {failed_count} 个")
    print(f"  - 总计: {len(episode_data_list)} 个")
    
    if success_count > 0:
        print(f"\n最终文件（完成处理目录）:")
        completed_dir = Path(config['paths'].get('completed', 'data/completed'))
        for episode_data in episode_data_list:
            episode_name = Path(episode_data['mp3_path']).stem
            print(f"  - {episode_name}:")
            print(f"    MP3: {completed_dir / f'{episode_name}_final.mp3'}")
            print(f"    TXT: {completed_dir / f'{episode_name}_final.txt'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

