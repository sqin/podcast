"""音频编辑模块 - 使用FFmpeg去除广告片段"""
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple
from .utils import ensure_dir

logger = logging.getLogger(__name__)


class AudioEditor:
    """音频编辑器 - 使用FFmpeg"""
    
    def __init__(self, ffmpeg_path=None):
        """
        初始化音频编辑器
        :param ffmpeg_path: FFmpeg可执行文件路径，如果为None则使用系统PATH中的ffmpeg
        """
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                logger.info(f"FFmpeg可用: {version_line}")
            else:
                raise Exception("FFmpeg检查失败")
        except FileNotFoundError:
            raise Exception(f"未找到FFmpeg，请确保已安装FFmpeg并在PATH中，或指定ffmpeg_path参数")
        except Exception as e:
            raise Exception(f"FFmpeg检查失败: {e}")
    
    def get_audio_duration(self, audio_path):
        """获取音频文件时长（秒）"""
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", str(audio_path),
                "-f", "null",
                "-"
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # FFmpeg将时长信息输出到stderr
            output = result.stderr
            
            # 从stderr中提取时长信息
            for line in output.split('\n'):
                if 'Duration:' in line:
                    duration_str = line.split('Duration:')[1].split(',')[0].strip()
                    # 解析 HH:MM:SS.mmm 格式
                    parts = duration_str.split(':')
                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    return total_seconds
            
            raise Exception("无法从FFmpeg输出中提取时长信息")
        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            raise
    
    def remove_ads(self, input_path, ad_segments: List[Tuple[float, float]], 
                   output_path=None, output_dir="data/processed"):
        """
        去除音频中的广告片段
        
        :param input_path: 输入MP3文件路径
        :param ad_segments: 广告时间段列表，格式为 [(start_sec, end_sec), ...]
        :param output_path: 输出文件路径，如果为None则自动生成
        :param output_dir: 输出目录（当output_path为None时使用）
        :return: 输出文件路径
        """
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                raise FileNotFoundError(f"输入文件不存在: {input_path}")
            
            # 获取音频总时长
            total_duration = self.get_audio_duration(input_path)
            logger.info(f"音频总时长: {total_duration:.2f}秒")
            
            # 如果没有广告片段，直接复制文件
            if not ad_segments:
                logger.info("没有广告片段，直接复制文件")
                if output_path is None:
                    output_dir = ensure_dir(output_dir)
                    output_path = Path(output_dir) / f"{input_path.stem}_no_ads{input_path.suffix}"
                else:
                    output_path = Path(output_path)
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._copy_file(input_path, output_path)
                return str(output_path)
            
            # 排序广告时间段
            ad_segments = sorted(ad_segments, key=lambda x: x[0])
            logger.info(f"需要去除 {len(ad_segments)} 个广告片段")
            
            # 计算需要保留的片段（非广告部分）
            keep_segments = self._calculate_keep_segments(ad_segments, total_duration)
            
            if not keep_segments:
                raise Exception("去除广告后没有剩余内容")
            
            logger.info(f"将保留 {len(keep_segments)} 个片段")
            for i, (start, end) in enumerate(keep_segments, 1):
                logger.info(f"  片段 {i}: {start:.2f}秒 - {end:.2f}秒 (时长: {end-start:.2f}秒)")
            
            # 生成输出路径
            if output_path is None:
                output_dir = ensure_dir(output_dir)
                output_path = Path(output_dir) / f"{input_path.stem}_no_ads{input_path.suffix}"
            else:
                output_path = Path(output_path)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用FFmpeg去除广告
            if len(keep_segments) == 1:
                # 只有一个片段，直接提取
                self._extract_segment(input_path, keep_segments[0], output_path)
            else:
                # 多个片段，需要合并
                self._extract_and_merge_segments(input_path, keep_segments, output_path)
            
            logger.info(f"去除广告完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"去除广告失败: {e}")
            raise
    
    def _calculate_keep_segments(self, ad_segments: List[Tuple[float, float]], 
                                 total_duration: float) -> List[Tuple[float, float]]:
        """计算需要保留的片段（非广告部分）"""
        keep_segments = []
        current_start = 0.0
        
        for ad_start, ad_end in ad_segments:
            # 如果广告开始时间大于当前起始时间，说明中间有需要保留的内容
            if ad_start > current_start:
                keep_segments.append((current_start, ad_start))
            
            # 更新当前起始时间为广告结束时间
            current_start = max(current_start, ad_end)
        
        # 如果最后还有剩余内容
        if current_start < total_duration:
            keep_segments.append((current_start, total_duration))
        
        return keep_segments
    
    def _extract_segment(self, input_path: Path, segment: Tuple[float, float], 
                        output_path: Path):
        """提取单个音频片段"""
        start, end = segment
        duration = end - start
        
        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-ss", str(start),
            "-t", str(duration),
            "-acodec", "copy",  # 使用copy避免重新编码
            "-y",  # 覆盖输出文件
            str(output_path)
        ]
        
        logger.info(f"提取片段: {start:.2f}秒 - {end:.2f}秒")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg提取失败: {result.stderr}")
    
    def _extract_and_merge_segments(self, input_path: Path, 
                                    segments: List[Tuple[float, float]], 
                                    output_path: Path):
        """提取多个片段并合并"""
        import tempfile
        
        # 创建临时目录存储片段
        temp_dir = Path(tempfile.mkdtemp())
        segment_files = []
        
        try:
            # 提取每个片段
            for i, (start, end) in enumerate(segments):
                segment_file = temp_dir / f"segment_{i:03d}.mp3"
                self._extract_segment(input_path, (start, end), segment_file)
                segment_files.append(segment_file)
            
            # 创建concat文件列表
            concat_file = temp_dir / "concat_list.txt"
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment_file in segment_files:
                    # 使用绝对路径，并转义特殊字符
                    abs_path = segment_file.resolve()
                    f.write(f"file '{abs_path}'\n")
            
            # 使用concat demuxer合并
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-acodec", "copy",
                "-y",
                str(output_path)
            ]
            
            logger.info(f"合并 {len(segments)} 个片段")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg合并失败: {result.stderr}")
                
        finally:
            # 清理临时文件
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
    
    def _copy_file(self, src: Path, dst: Path):
        """复制文件"""
        import shutil
        shutil.copy2(src, dst)

