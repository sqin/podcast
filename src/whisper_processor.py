"""Whisper转录处理模块"""
import whisper
import logging
from pathlib import Path
from .utils import ensure_dir

logger = logging.getLogger(__name__)


class WhisperProcessor:
    """Whisper处理器"""
    
    def __init__(self, small_model="tiny", large_model="large-v3", device="cuda", single_model=None):
        self.small_model = small_model
        self.large_model = large_model
        self.device = device
        self.single_model = single_model  # 如果指定，则使用单个模型（向后兼容）
        self._small_model_instance = None
        self._large_model_instance = None
        self._single_model_instance = None
    
    def _load_model(self, model_name):
        """加载Whisper模型"""
        try:
            logger.info(f"正在加载Whisper模型: {model_name} (device: {self.device})")
            model = whisper.load_model(model_name, device=self.device)
            logger.info(f"模型加载成功: {model_name}")
            return model
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    def get_small_model(self):
        """获取small模型实例（懒加载）"""
        if self._small_model_instance is None:
            self._small_model_instance = self._load_model(self.small_model)
        return self._small_model_instance
    
    def get_large_model(self):
        """获取large模型实例（懒加载）"""
        if self._large_model_instance is None:
            self._large_model_instance = self._load_model(self.large_model)
        return self._large_model_instance
    
    def get_single_model(self):
        """获取单个模型实例（懒加载）"""
        if self.single_model is None:
            # 如果没有指定，使用large_model
            self.single_model = self.large_model
        if self._single_model_instance is None:
            self._single_model_instance = self._load_model(self.single_model)
        return self._single_model_instance
    
    def generate_both(self, audio_path, srt_output_dir="transcripts/srt", txt_output_dir="transcripts/txt"):
        """使用单个模型同时生成SRT和TXT文件"""
        try:
            logger.info(f"开始同时生成SRT和TXT文件: {audio_path}")
            
            # 确保输出目录存在
            srt_output_dir = ensure_dir(srt_output_dir)
            txt_output_dir = ensure_dir(txt_output_dir)
            
            # 生成输出文件名
            audio_name = Path(audio_path).stem
            srt_filename = f"{audio_name}.srt"
            txt_filename = f"{audio_name}.txt"
            
            srt_path = Path(srt_output_dir) / srt_filename
            txt_path = Path(txt_output_dir) / txt_filename
            
            # 如果文件已存在，警告
            if srt_path.exists():
                logger.warning(f"SRT文件已存在，将覆盖: {srt_path}")
            if txt_path.exists():
                logger.warning(f"TXT文件已存在，将覆盖: {txt_path}")
            
            # 加载模型并转录（只转录一次）
            model = self.get_single_model()
            logger.info(f"使用模型 {self.single_model} 开始转录音频...")
            result = model.transcribe(audio_path, verbose=True)
            
            # 生成SRT格式
            srt_content = self._result_to_srt(result)
            
            # 提取文本
            text = result.get('text', '').strip()
            
            # 保存SRT文件
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            # 保存TXT文件
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"SRT文件生成完成: {srt_path}")
            logger.info(f"TXT文件生成完成: {txt_path}")
            return str(srt_path), str(txt_path)
            
        except Exception as e:
            logger.error(f"同时生成SRT和TXT失败: {e}")
            raise
    
    def generate_srt(self, audio_path, output_dir="transcripts/srt", output_filename=None):
        """使用whisper small模型生成SRT文件"""
        try:
            logger.info(f"开始生成SRT文件: {audio_path}")
            
            # 确保输出目录存在
            output_dir = ensure_dir(output_dir)
            
            # 生成输出文件名
            if not output_filename:
                audio_name = Path(audio_path).stem
                output_filename = f"{audio_name}.srt"
            
            output_path = Path(output_dir) / output_filename
            
            # 如果文件已存在，询问是否覆盖（这里直接覆盖）
            if output_path.exists():
                logger.warning(f"SRT文件已存在，将覆盖: {output_path}")
            
            # 加载模型并转录
            model = self.get_small_model()
            logger.info("开始转录音频...")
            result = model.transcribe(audio_path, verbose=True)
            
            # 生成SRT格式
            srt_content = self._result_to_srt(result)
            
            # 保存SRT文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"SRT文件生成完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"SRT生成失败: {e}")
            raise
    
    def generate_txt(self, audio_path, output_dir="transcripts/txt", output_filename=None):
        """使用whisper large-v3模型生成TXT文件"""
        try:
            logger.info(f"开始生成TXT文件: {audio_path}")
            
            # 确保输出目录存在
            output_dir = ensure_dir(output_dir)
            
            # 生成输出文件名
            if not output_filename:
                audio_name = Path(audio_path).stem
                output_filename = f"{audio_name}.txt"
            
            output_path = Path(output_dir) / output_filename
            
            # 如果文件已存在，询问是否覆盖（这里直接覆盖）
            if output_path.exists():
                logger.warning(f"TXT文件已存在，将覆盖: {output_path}")
            
            # 加载模型并转录
            model = self.get_large_model()
            logger.info("开始转录音频...")
            result = model.transcribe(audio_path, verbose=True)
            
            # 提取文本
            text = result.get('text', '').strip()
            
            # 保存TXT文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"TXT文件生成完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"TXT生成失败: {e}")
            raise
    
    def _result_to_srt(self, result):
        """将Whisper结果转换为SRT格式"""
        srt_lines = []
        segments = result.get('segments', [])
        
        for i, segment in enumerate(segments, start=1):
            start_time = self._format_timestamp(segment['start'])
            end_time = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")  # 空行分隔
        
        return "\n".join(srt_lines)
    
    def _format_timestamp(self, seconds):
        """将秒数转换为SRT时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

