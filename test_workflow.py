"""测试完整工作流：RSS下载、Whisper生成、大模型处理"""
import sys
import os
from pathlib import Path
from src.utils import setup_logging, load_config
from src.rss_parser import RSSParser
from src.whisper_processor import WhisperProcessor
from src.llm_processor import LLMProcessor
from src.audio_editor import AudioEditor
from src.text_editor import TextEditor


def test_rss_download():
    """获取最新episode（如果已下载则直接使用，否则下载）"""
    print("\n" + "=" * 60)
    print("步骤 1: 获取最新episode")
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
    
    # 获取最新的episode
    print("\n正在检查最新episode...")
    latest_episode = parser.get_latest_episode()
    
    if not latest_episode:
        print("\n✗ 未找到episode")
        return None
    
    # 检查最新episode是否已下载
    if parser.is_episode_downloaded(latest_episode):
        print(f"\n✓ 最新episode已下载，直接使用")
        title = latest_episode.get('title', 'Unknown')
        pub_date = latest_episode.get('published', '')
        
        # 从记录中获取MP3路径
        episode_id = parser._get_episode_id(latest_episode)
        if episode_id in parser.downloaded_episodes:
            mp3_path = parser.downloaded_episodes[episode_id]['mp3_path']
            print(f"  标题: {title}")
            print(f"  MP3路径: {mp3_path}")
            return {
                'title': title,
                'pub_date': pub_date,
                'mp3_path': mp3_path,
                'episode': latest_episode
            }
        else:
            # 如果记录中没有路径，尝试从文件名查找
            from src.utils import sanitize_filename
            safe_title = sanitize_filename(title)
            mp3_path = Path(parser.download_dir) / f"{safe_title}.mp3"
            if mp3_path.exists():
                print(f"  标题: {title}")
                print(f"  MP3路径: {mp3_path}")
                return {
                    'title': title,
                    'pub_date': pub_date,
                    'mp3_path': str(mp3_path),
                    'episode': latest_episode
                }
    else:
        # 未下载，下载最新episode
        print(f"\n最新episode未下载，开始下载...")
        print(f"  标题: {latest_episode.get('title', 'Unknown')}")
        try:
            episode_data = parser._download_single_episode(latest_episode)
            if episode_data:
                print(f"  ✓ 下载完成: {episode_data['mp3_path']}")
                return episode_data
        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
            return None
    
    # 如果以上都失败，尝试从本地文件查找
    print("\n尝试从本地文件查找...")
    raw_audio_dir = Path(config['paths']['raw_audio'])
    mp3_files = list(raw_audio_dir.glob("*.mp3"))
    if mp3_files:
        # 按修改时间排序，使用最新的
        mp3_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        print(f"找到已下载的MP3文件，使用最新的: {mp3_files[0]}")
        return {
            'title': mp3_files[0].stem,
            'mp3_path': str(mp3_files[0])
        }
    
    return None


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


def main():
    """主测试函数"""
    import argparse
    
    parser_cmd = argparse.ArgumentParser(description='播客工作流测试脚本')
    # 移除count参数，工作流默认只处理最新episode
    args = parser_cmd.parse_args()
    
    print("=" * 60)
    print("播客工作流测试脚本")
    print("=" * 60)
    print("\n本脚本将执行以下工作流：")
    print("  1. RSS下载MP3（如果已下载则跳过）")
    print("  2. Whisper使用最小模型生成SRT文件（用于识别片头片尾）")
    print("  3. 大模型识别片头片尾时间段")
    print("  4. 根据时间戳去除片头片尾，生成新MP3")
    print("  5. 使用处理后的MP3和large模型生成最终TXT文件（删除片头片尾内容）")
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
    
    # 步骤1: 获取最新episode（已下载则使用，未下载则下载）
    episode_data = test_rss_download()
    
    # 如果今天没有新episode，允许用户指定一个MP3文件
    mp3_path = None
    if episode_data:
        mp3_path = episode_data['mp3_path']
        title = episode_data['title']
    else:
        # 检查是否有已下载的MP3文件
        raw_audio_dir = Path(config['paths']['raw_audio'])
        mp3_files = list(raw_audio_dir.glob("*.mp3"))
        if mp3_files:
            print(f"\n找到已下载的MP3文件，使用最新的: {mp3_files[0]}")
            mp3_path = str(mp3_files[0])
            title = mp3_files[0].stem
        else:
            print("\n没有可用的MP3文件，测试结束")
            return
    
    # 步骤2: Whisper生成SRT（使用最小模型）
    srt_path = test_whisper_generation(mp3_path)
    
    if not srt_path:
        print("\nWhisper生成失败，工作流终止")
        return
    
    # 步骤3-4: 大模型处理（识别片头片尾、去除音频）
    processed_mp3_path, segments_to_remove = test_llm_processing(
        srt_path, mp3_path=mp3_path, title=title if 'title' in locals() else None
    )
    
    if not processed_mp3_path:
        print("\n音频处理失败，工作流终止")
        return
    
    # 步骤5: 使用处理后的MP3生成最终TXT文件
    final_txt_path = test_generate_final_txt(
        processed_mp3_path, srt_path, segments_to_remove, 
        title=title if 'title' in locals() else None
    )
    
    if not final_txt_path:
        print("\nTXT生成失败，工作流终止")
        return
    
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
    
    # 总结
    print("\n" + "=" * 60)
    print("工作流完成！")
    print("=" * 60)
    print("\n最终文件（完成处理目录）:")
    completed_dir = Path(config['paths'].get('completed', 'data/completed'))
    episode_name = Path(mp3_path).stem
    print(f"  - MP3: {completed_dir / f'{episode_name}_final.mp3'}")
    print(f"  - TXT: {completed_dir / f'{episode_name}_final.txt'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

