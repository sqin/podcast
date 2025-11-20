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
            # 支持连续文本（不是按行）
            filtered_text = original_text
            removed_count = 0
            
            # 按文本长度排序，先删除长的片段（避免短片段被长片段包含）
            sorted_texts = sorted(texts_to_remove, key=len, reverse=True)
            
            logger.info(f"开始删除 {len(sorted_texts)} 个文本片段")
            
            for idx, text_to_remove in enumerate(sorted_texts, 1):
                text_to_remove_clean = text_to_remove.strip()
                if not text_to_remove_clean:
                    continue
                
                original_length = len(filtered_text)
                matched = False
                
                # 策略1: 直接文本匹配（忽略大小写）
                pattern1 = re.escape(text_to_remove_clean)
                if re.search(pattern1, filtered_text, re.IGNORECASE):
                    filtered_text = re.sub(pattern1, '', filtered_text, flags=re.IGNORECASE)
                    if len(filtered_text) < original_length:
                        removed_count += 1
                        matched = True
                        logger.debug(f"[{idx}/{len(sorted_texts)}] 删除（直接匹配）: {text_to_remove_clean[:60]}...")
                
                # 策略2: 如果直接匹配失败，尝试去除标点符号和空格后匹配
                if not matched:
                    # 去除标点符号和多余空格
                    text_clean = re.sub(r'[^\w\s]', '', text_to_remove_clean)
                    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
                    
                    if len(text_clean) > 10:  # 只对较长的文本使用此策略
                        # 在原文中查找（去除标点后）
                        original_clean = re.sub(r'[^\w\s]', '', filtered_text)
                        original_clean = re.sub(r'\s+', ' ', original_clean)
                        
                        if text_clean.lower() in original_clean.lower():
                            # 找到匹配位置
                            match_idx = original_clean.lower().find(text_clean.lower())
                            if match_idx != -1:
                                # 计算在原始文本中的大致位置
                                # 通过字符计数找到对应位置
                                clean_char_count = 0
                                for i, char in enumerate(filtered_text):
                                    if char.isalnum() or char.isspace():
                                        clean_char_count += 1
                                        if clean_char_count >= match_idx:
                                            # 找到匹配开始位置
                                            match_start = max(0, i - 20)  # 向前扩展20字符
                                            match_end = min(len(filtered_text), i + len(text_to_remove_clean) + 100)  # 向后扩展
                                            
                                            # 尝试找到完整的句子边界
                                            sentence_start = max(0, filtered_text.rfind('.', 0, match_start))
                                            if sentence_start == -1:
                                                sentence_start = match_start
                                            else:
                                                sentence_start += 1
                                            
                                            sentence_end = filtered_text.find('.', match_end - 100)
                                            if sentence_end == -1:
                                                sentence_end = match_end
                                            else:
                                                sentence_end += 1
                                            
                                            # 删除这个范围
                                            filtered_text = filtered_text[:sentence_start] + filtered_text[sentence_end:]
                                            removed_count += 1
                                            matched = True
                                            logger.debug(f"[{idx}/{len(sorted_texts)}] 删除（清理匹配）: {text_to_remove_clean[:60]}...")
                                            break
                
                # 策略3: 关键词匹配（如果前两种都失败）
                if not matched and len(text_to_remove_clean) > 15:
                    words = re.findall(r'\b\w{4,}\b', text_to_remove_clean.lower())  # 提取4字符以上的词
                    if len(words) >= 3:
                        # 检查原文中是否包含至少3个这些关键词
                        text_lower = filtered_text.lower()
                        matched_words = sum(1 for word in words[:5] if word in text_lower)
                        if matched_words >= 3:
                            # 找到包含这些关键词的句子并删除
                            # 使用第一个关键词的位置
                            first_word = words[0]
                            word_pos = text_lower.find(first_word)
                            if word_pos != -1:
                                # 扩展删除范围
                                sentence_start = max(0, filtered_text.rfind('.', 0, word_pos))
                                if sentence_start == -1:
                                    sentence_start = max(0, word_pos - 100)
                                else:
                                    sentence_start += 1
                                
                                sentence_end = filtered_text.find('.', word_pos)
                                if sentence_end == -1:
                                    sentence_end = min(len(filtered_text), word_pos + 200)
                                else:
                                    sentence_end += 1
                                
                                filtered_text = filtered_text[:sentence_start] + filtered_text[sentence_end:]
                                removed_count += 1
                                matched = True
                                logger.debug(f"[{idx}/{len(sorted_texts)}] 删除（关键词匹配）: {text_to_remove_clean[:60]}...")
            
            # 清理多余的空格（保留句子结构）
            filtered_text = re.sub(r' +', ' ', filtered_text)  # 多个空格合并为一个
            filtered_text = re.sub(r'\s+([.,!?;:])', r'\1', filtered_text)  # 标点前的空格
            filtered_text = filtered_text.strip()
            
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

