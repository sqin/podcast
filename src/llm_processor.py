"""大模型处理模块 - 使用通义千问API"""
import dashscope
import logging
import json
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class LLMProcessor:
    """大模型处理器 - 使用通义千问"""
    
    def __init__(self, api_key, model="qwen-turbo"):
        self.api_key = api_key
        self.model = model
        dashscope.api_key = api_key
        logger.info(f"初始化LLM处理器，模型: {model}")
    
    def _call_api(self, messages, temperature=0.7, max_tokens=2000, enable_search=False):
        """调用通义千问API"""
        try:
            # 构建API参数
            api_params = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'result_format': 'message'
            }
            
            # 如果模型支持，启用搜索增强（部分模型支持）
            if enable_search and hasattr(dashscope.Generation, 'call'):
                # 某些模型支持enable_search参数
                pass
            
            response = dashscope.Generation.call(**api_params)
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                logger.error(f"API调用失败: {response.status_code}, {response.message}")
                raise Exception(f"API调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            raise
    
    def detect_ads(self, srt_path):
        """基于大模型识别SRT文件中的片头片尾时间段"""
        try:
            logger.info(f"开始识别片头片尾时间段: {srt_path}")
            
            # 读取SRT文件内容
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # 构建提示词 - 使用链式思考（Chain of Thought）提升准确性
            prompt = f"""你是一个专业的播客内容分析专家。请仔细分析以下SRT字幕文件，识别片头和片尾时间段。

## 分析步骤（请按此步骤思考）：

### 第一步：识别片头
片头特征：
- 通常以问候语开始，如："Hey, Michelle, how are you today?"、"Hey there, Michelle. What's shakin'?"、"Hey, Lindsay, how are you?"、"Hey Aubrey, how are you today?"、"Hey Lindsay, how's it going today?"
- 模式：hey/hello + 人名 + 问候语
- 片头通常包含：节目介绍、主持人介绍、开场白等
- 片头结束标志：开始进入正题内容

### 第二步：识别片尾
片尾特征：
- 通常以告别语结束，如："bye"、"see you"、"next time"、"goodbye" + 人名
- 模式：bye/goodbye/see you + 人名 + 告别语
- 片尾通常包含：总结、下期预告、感谢、结束语等
- 片尾开始标志：正题内容结束，开始告别

### 第三步：提取时间段
- 仔细查看SRT文件中的时间戳
- 找到片头的开始时间（第一个问候语出现的时间）和结束时间（进入正题的时间）
- 找到片尾的开始时间（开始告别的时间）和结束时间（最后一个告别语的时间）

## SRT文件内容：
{srt_content}

## 输出要求：
请以JSON格式返回结果，格式如下：
{{
  "ad_segments": [
    {{
      "start_time": "00:00:00,000",
      "end_time": "00:01:30,000",
      "reason": "片头：包含问候语和节目介绍"
    }},
    {{
      "start_time": "00:15:00,000",
      "end_time": "00:16:00,000",
      "reason": "片尾：包含告别语和结束语"
    }}
  ]
}}

注意：
- 时间格式必须严格按照SRT格式：HH:MM:SS,mmm
- 如果没有片头或片尾，返回空的ad_segments数组
- 只返回JSON，不要其他文字说明
- 请仔细核对时间戳，确保准确性"""
            
            messages = [
                {
                    "role": "system",
                    "content": """你是一个专业的播客内容分析专家，具有以下能力：
1. 准确识别播客的片头和片尾时间段
2. 理解SRT字幕文件的时间戳格式
3. 识别问候语、告别语等关键语言模式
4. 精确提取时间段信息

请仔细分析，确保时间戳的准确性。"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 调用API - 降低temperature以提高准确性，增加max_tokens以允许更详细的思考
            response_text = self._call_api(messages, temperature=0.1, max_tokens=3000)
            
            # 解析JSON响应
            # 尝试提取JSON部分（去除可能的markdown代码块标记）
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
            else:
                json_str = response_text
            
            result = json.loads(json_str)
            ad_segments = result.get('ad_segments', [])
            
            # 转换为秒数格式的元组列表
            ad_times = []
            for segment in ad_segments:
                start_sec = self._srt_time_to_seconds(segment['start_time'])
                end_sec = self._srt_time_to_seconds(segment['end_time'])
                ad_times.append((start_sec, end_sec))
                logger.info(f"识别到片头片尾片段: {segment['start_time']} - {segment['end_time']} ({segment.get('reason', '')})")
            
            logger.info(f"共识别到 {len(ad_times)} 个片头片尾片段")
            return ad_times
            
        except Exception as e:
            logger.error(f"片头片尾识别失败: {e}")
            raise
    
    def _split_text_into_chunks(self, text, max_chunk_size=3000):
        """将文本分割成多个块，尽量在句子边界处分割"""
        # 如果文本较短，直接返回
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 按句子分割（句号、问号、感叹号）
        sentences = re.split(r'([.!?]\s+)', text)
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # 包含标点和空格
            
            # 如果当前块加上新句子不超过限制，添加到当前块
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence
            else:
                # 保存当前块，开始新块
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_transcript(self, txt_path, title=None):
        """处理转录文本：添加人名、分段、翻译（支持分段处理）"""
        try:
            logger.info(f"开始处理转录文本: {txt_path}")
            
            # 读取TXT文件内容
            with open(txt_path, 'r', encoding='utf-8') as f:
                transcript = f.read()
            
            transcript_length = len(transcript)
            logger.info(f"原始文本长度: {transcript_length} 字符")
            
            # 如果文本较长，分段处理
            max_chunk_size = 3000  # 每个分块最大字符数（约1500-2000单词）
            chunks = self._split_text_into_chunks(transcript, max_chunk_size)
            
            if len(chunks) > 1:
                logger.info(f"文本较长，将分成 {len(chunks)} 段进行处理")
                processed_chunks = []
                
                for i, chunk in enumerate(chunks, 1):
                    logger.info(f"处理第 {i}/{len(chunks)} 段（长度: {len(chunk)} 字符）...")
                    processed_chunk = self._process_single_chunk(chunk, title, chunk_index=i, total_chunks=len(chunks))
                    processed_chunks.append(processed_chunk)
                
                # 合并所有处理后的段落
                processed_content = "\n\n---\n\n".join(processed_chunks)
                logger.info(f"所有段落处理完成，总长度: {len(processed_content)} 字符")
            else:
                # 文本较短，直接处理
                logger.info("文本较短，直接处理")
                processed_content = self._process_single_chunk(transcript, title)
            
            logger.info("转录文本处理完成")
            return processed_content
            
        except Exception as e:
            logger.error(f"转录文本处理失败: {e}")
            raise
    
    def _process_single_chunk(self, chunk_text, title=None, chunk_index=None, total_chunks=None):
        """处理单个文本块"""
        # 构建提示词
        chunk_info = ""
        if chunk_index and total_chunks:
            chunk_info = f"\n注意：这是第 {chunk_index}/{total_chunks} 段，请保持格式一致，不要添加'段首'或'段尾'标记。"
        
        prompt = f"""你是一个专业的播客内容处理专家。请仔细处理以下英文播客转录文本。

## 处理步骤：

### 第一步：识别说话人
仔细分析文本，识别不同的说话人：
- 常见说话人：Lindsay、Michelle、Aubrey等
- 注意说话人的语言风格、用词习惯
- 如果无法确定说话人，使用【说话人】或【主持人】

### 第二步：理解内容
- 理解每段对话的上下文
- 识别话题转换点
- 理解说话人的意图和语气

### 第三步：合理分段
- 按照话题自然分段
- 每段3-5句话，保持逻辑完整
- 在话题转换处分段

### 第四步：翻译
- 翻译自然流畅，符合中文表达习惯
- 保持原文的语气和风格（正式/非正式、幽默/严肃等）
- 保留重要的英文术语（如专业词汇、品牌名）并加括号说明
- 注意文化差异，使用地道的中文表达

播客标题：{title if title else '未知'}{chunk_info}

转录文本：
{chunk_text}

## 输出格式：

【说话人1】：
[英文原文]
[中文翻译]

【说话人2】：
[英文原文]
[中文翻译]

...

重要：每段必须包含英文原文和中文翻译两部分，英文原文在上，中文翻译在下。

## 质量要求：
- 准确识别说话人，不要混淆
- 每段必须包含完整的英文原文和中文翻译
- 翻译准确、自然、流畅
- 分段合理，逻辑清晰
- 保持原文的语气和风格"""
        
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的播客内容处理专家，具有以下能力：
1. 准确识别不同说话人的语言特征和说话风格
2. 理解对话的上下文和逻辑关系
3. 进行自然流畅的中文翻译，保持原文语气
4. 合理分段，保持逻辑完整性

请仔细分析，确保翻译质量和分段合理性。"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # 估算max_tokens：原文长度 + 翻译后长度（通常翻译后会更长）
        estimated_tokens = len(chunk_text) * 2  # 英文+中文，大约2倍
        max_tokens = max(6000, estimated_tokens // 4)  # 至少6000，根据内容动态调整
        
        if chunk_index:
            logger.debug(f"第 {chunk_index} 段：估算需要 {estimated_tokens} tokens，设置max_tokens为 {max_tokens}")
        
        processed_content = self._call_api(messages, temperature=0.5, max_tokens=max_tokens)
        
        # 检查返回内容是否完整
        if processed_content.endswith('...') or len(processed_content) < len(chunk_text) * 0.3:
            logger.warning(f"返回内容可能不完整，长度: {len(processed_content)}，原始长度: {len(chunk_text)}")
        
        return processed_content
    
    def _srt_time_to_seconds(self, srt_time):
        """将SRT时间格式转换为秒数"""
        # 格式: HH:MM:SS,mmm
        try:
            time_part, millis = srt_time.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            total_seconds = hours * 3600 + minutes * 60 + seconds + int(millis) / 1000.0
            return total_seconds
        except Exception as e:
            logger.error(f"时间格式转换失败: {srt_time}, {e}")
            return 0.0

