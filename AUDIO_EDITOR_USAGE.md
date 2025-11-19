# 音频编辑功能使用说明

## 功能概述

音频编辑模块 (`src/audio_editor.py`) 使用FFmpeg去除MP3文件中的广告片段，根据识别到的广告时间段自动提取非广告部分并合并成新的MP3文件。

## 主要功能

### `AudioEditor` 类

#### `__init__(ffmpeg_path=None)`
初始化音频编辑器
- `ffmpeg_path`: FFmpeg可执行文件路径（可选，默认使用系统PATH中的ffmpeg）

#### `remove_ads(input_path, ad_segments, output_path=None, output_dir="data/processed")`
去除音频中的广告片段
- `input_path`: 输入MP3文件路径
- `ad_segments`: 广告时间段列表，格式为 `[(start_sec, end_sec), ...]`
- `output_path`: 输出文件路径（可选，如果为None则自动生成）
- `output_dir`: 输出目录（当output_path为None时使用）
- 返回: 输出文件路径

#### `get_audio_duration(audio_path)`
获取音频文件时长（秒）

## 使用方法

### 1. 在代码中使用

```python
from src.audio_editor import AudioEditor
from src.llm_processor import LLMProcessor

# 识别广告
llm_processor = LLMProcessor(api_key="your-api-key", model="qwen3-max")
ad_segments = llm_processor.detect_ads("transcripts/srt/episode.srt")

# 去除广告
editor = AudioEditor()
processed_mp3 = editor.remove_ads(
    input_path="data/raw/episode.mp3",
    ad_segments=ad_segments,
    output_dir="data/processed"
)

print(f"处理后的文件: {processed_mp3}")
```

### 2. 使用测试脚本

#### 完整工作流测试（包含去除广告）
```bash
python test_workflow.py
```

#### 单独测试音频编辑功能
```bash
python test_audio_editor.py
```

## 工作原理

1. **计算保留片段**: 根据广告时间段列表，计算需要保留的非广告片段
2. **提取片段**: 使用FFmpeg提取每个保留片段
3. **合并片段**: 如果有多个片段，使用FFmpeg的concat demuxer合并

### 示例

假设音频总时长为600秒，识别到以下广告片段：
- 广告1: 100秒 - 120秒
- 广告2: 300秒 - 330秒

则保留的片段为：
- 片段1: 0秒 - 100秒
- 片段2: 120秒 - 300秒
- 片段3: 330秒 - 600秒

最终会提取这3个片段并合并成新的MP3文件。

## 输出文件

处理后的MP3文件保存在 `data/processed/` 目录，文件名格式为：
`{原始文件名}_no_ads.mp3`

例如：
- 原始文件: `data/raw/Episode_2515.mp3`
- 处理后: `data/processed/Episode_2515_no_ads.mp3`

## 注意事项

1. **FFmpeg要求**: 需要系统已安装FFmpeg，并在PATH中可用
2. **文件格式**: 目前支持MP3格式，使用copy编码避免重新编码
3. **处理时间**: 根据音频长度和片段数量，处理时间可能较长
4. **临时文件**: 处理多个片段时会创建临时文件，处理完成后自动清理

## 故障排除

### 问题1: FFmpeg未找到
**错误**: `未找到FFmpeg，请确保已安装FFmpeg并在PATH中`

**解决**:
- Windows: 下载FFmpeg并添加到系统PATH
- Linux: `sudo apt-get install ffmpeg` 或 `sudo yum install ffmpeg`
- macOS: `brew install ffmpeg`

### 问题2: 处理失败
**可能原因**:
- 广告时间段超出音频长度
- 广告时间段重叠或顺序错误
- 音频文件损坏

**解决**: 检查广告时间段是否正确，确保在音频长度范围内

### 问题3: 输出文件过大或过小
**可能原因**: 广告识别不准确

**解决**: 检查SRT文件和广告识别结果，手动调整广告时间段

## 性能优化

1. **单片段优化**: 如果只有一个保留片段，直接提取，无需合并
2. **编码优化**: 使用 `-acodec copy` 避免重新编码，保持原始音质
3. **临时文件**: 使用系统临时目录，处理完成后自动清理

## 完整工作流示例

```python
from src.rss_parser import RSSParser
from src.whisper_processor import WhisperProcessor
from src.llm_processor import LLMProcessor
from src.audio_editor import AudioEditor
from src.utils import load_config

config = load_config()

# 1. 下载episode
parser = RSSParser(feed_url=config['rss']['feed_url'])
episodes = parser.download_episodes(count=1)
mp3_path = episodes[0]['mp3_path']

# 2. 生成SRT
whisper = WhisperProcessor()
srt_path = whisper.generate_srt(mp3_path)

# 3. 识别广告
llm = LLMProcessor(api_key=config['llm']['api_key'])
ad_segments = llm.detect_ads(srt_path)

# 4. 去除广告
editor = AudioEditor()
processed_mp3 = editor.remove_ads(
    input_path=mp3_path,
    ad_segments=ad_segments,
    output_dir=config['paths']['processed_audio']
)

print(f"处理完成: {processed_mp3}")
```

