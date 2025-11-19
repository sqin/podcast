"""文本编辑模块 - 从TXT中删除片头片尾内容"""
import logging
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class TextEditor:
    """文本编辑器"""
    
    def __init__(self):
        pass
    
    def _srt_time_to_seconds(self, srt_time):
        """将SRT时间格式转换为秒数"""
        try:
            time_part, millis = srt_time.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            total_seconds = hours * 3600 + minutes * 60 + seconds + int(millis) / 1000.0
            return total_seconds
        except Exception as e:
            logger.error(f"时间格式转换失败: {srt_time}, {e}")
            return 0.0
    
    def _parse_srt(self, srt_path):
        """解析SRT文件，返回时间段和文本的映射"""
        segments = []
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析SRT格式：序号、时间、文本
        pattern = r'(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\Z)'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            seq = int(match.group(1))
            start_time = match.group(2)
            end_time = match.group(3)
            text = match.group(4).strip()
            
            start_sec = self._srt_time_to_seconds(start_time)
            end_sec = self._srt_time_to_seconds(end_time)
            
            segments.append({
                'seq': seq,
                'start': start_sec,
                'end': end_sec,
                'text': text
            })
        
        return segments
    
    def remove_segments_from_txt(self, txt_path, srt_path, segments_to_remove: List[Tuple[float, float]], output_path=None):
        """
        从TXT文件中删除指定时间段对应的内容
        
        :param txt_path: 原始TXT文件路径
        :param srt_path: SRT文件路径（用于映射时间到文本）
        :param segments_to_remove: 要删除的时间段列表 [(start_sec, end_sec), ...]
        :param output_path: 输出文件路径，如果为None则覆盖原文件
        :return: 输出文件路径
        """
        try:
            logger.info(f"开始从TXT中删除片头片尾内容: {txt_path}")
            
            # 读取原始TXT
            with open(txt_path, 'r', encoding='utf-8') as f:
                original_text = f.read()
            
            # 解析SRT文件
            srt_segments = self._parse_srt(srt_path)
            logger.info(f"SRT文件包含 {len(srt_segments)} 个字幕片段")
            
            # 找出需要删除的文本片段
            texts_to_remove = set()
            for remove_start, remove_end in segments_to_remove:
                for seg in srt_segments:
                    # 如果字幕片段与要删除的时间段有重叠，则标记为删除
                    if not (seg['end'] <= remove_start or seg['start'] >= remove_end):
                        texts_to_remove.add(seg['text'].strip())
                        logger.debug(f"标记删除: {seg['text'][:50]}... (时间: {seg['start']:.2f}-{seg['end']:.2f})")
            
            logger.info(f"找到 {len(texts_to_remove)} 个需要删除的文本片段")
            
            # 从原始文本中删除这些片段
            # 按行处理，删除包含这些文本的行
            lines = original_text.split('\n')
            filtered_lines = []
            removed_count = 0
            
            for line in lines:
                line_stripped = line.strip()
                should_remove = False
                
                # 检查这一行是否包含要删除的文本
                for text_to_remove in texts_to_remove:
                    # 使用模糊匹配，因为文本可能有细微差异
                    if text_to_remove.lower() in line_stripped.lower() or line_stripped.lower() in text_to_remove.lower():
                        # 如果匹配度足够高（超过50%），则删除
                        if len(text_to_remove) > 0 and len(line_stripped) > 0:
                            similarity = min(len(text_to_remove), len(line_stripped)) / max(len(text_to_remove), len(line_stripped))
                            if similarity > 0.5:
                                should_remove = True
                                removed_count += 1
                                break
                
                if not should_remove:
                    filtered_lines.append(line)
            
            # 重新组合文本
            filtered_text = '\n'.join(filtered_lines)
            
            # 清理多余的空行（连续3个以上空行合并为2个）
            filtered_text = re.sub(r'\n{3,}', '\n\n', filtered_text)
            
            # 确定输出路径
            if output_path is None:
                output_path = txt_path
            else:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存处理后的文本
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(filtered_text)
            
            logger.info(f"已删除 {removed_count} 行，处理后的文本已保存到: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"从TXT中删除内容失败: {e}")
            raise

