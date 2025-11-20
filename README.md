# 播客自动处理工作流

自动化的播客处理工作流，从RSS feed解析到音频和文本处理完成。

## 功能特性

- **自动RSS解析**：从RSS feed获取最新episode，支持批量处理
- **智能去重**：自动记录已下载和已处理的episode，避免重复处理
- **Whisper转录**：
  - 使用最小模型（tiny）快速生成SRT文件（用于识别片头片尾）
  - 使用大模型（large-v3）生成最终TXT文件（英文原文）
- **片头片尾识别**：基于大模型（通义千问）自动识别片头片尾时间段
- **音频处理**：使用FFmpeg自动去除片头片尾片段
- **自动清理**：处理完成后自动清理中间文件，只保留最终结果

## 安装

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 安装FFmpeg（如果未安装）：
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载FFmpeg并添加到PATH环境变量
```

3. 配置`config.yaml`文件：
   - 设置RSS feed URL
   - 配置Whisper模型（min_model用于SRT，large_model用于TXT）
   - 填入通义千问API密钥
   - 配置文件路径

## 使用方法

### 基本使用

处理最近1个episode（默认）：
```bash
python test_workflow.py
```

### 命令行参数

- `--count N`：处理最近N个episode（默认：1）
- `--no-use-existing`：如果episode已下载，不使用已下载的，而是跳过（默认：使用已下载的）

示例：
```bash
# 处理最近3个episode
python test_workflow.py --count 3

# 处理最近2个episode，如果已下载则跳过
python test_workflow.py --count 2 --no-use-existing
```

## 工作流程

工作流会自动执行以下步骤：

1. **RSS解析**：从RSS feed获取episode列表
2. **去重检查**：
   - 检查episode是否已处理（如有记录则跳过）
   - 检查episode是否已下载（如已下载则直接使用）
3. **SRT生成**：使用最小模型生成SRT文件（用于识别片头片尾）
4. **片头片尾识别**：使用大模型分析SRT，识别片头片尾时间段
5. **音频处理**：使用FFmpeg去除片头片尾，生成新MP3
6. **TXT生成**：使用大模型对处理后的MP3生成最终TXT文件
7. **文件整理**：将最终MP3和TXT移动到完成目录
8. **记录保存**：记录处理完成信息到JSON文件
9. **清理中间文件**：删除SRT等临时文件

## 项目结构

```
podcast/
├── test_workflow.py       # 主工作流入口
├── config.yaml            # 配置文件
├── requirements.txt       # Python依赖
├── src/                   # 源代码模块
│   ├── rss_parser.py      # RSS解析和下载
│   ├── whisper_processor.py  # Whisper转录
│   ├── llm_processor.py   # 大模型处理（片头片尾识别）
│   ├── audio_editor.py    # 音频编辑（FFmpeg）
│   ├── text_editor.py     # 文本编辑
│   └── utils.py           # 工具函数
├── data/                  # 数据目录
│   ├── raw/               # 原始音频文件
│   ├── processed/         # 处理中的音频文件
│   ├── completed/         # 完成处理的最终文件
│   ├── downloaded_episodes.json  # 下载记录
│   └── processed_episodes.json   # 处理记录
├── transcripts/           # 转录文件
│   ├── srt/               # SRT字幕文件
│   └── txt/               # TXT文本文件
└── logs/                  # 日志文件
```

## 配置文件说明

`config.yaml` 主要配置项：

- `rss.feed_url`：RSS feed地址
- `whisper.min_model`：最小模型（用于快速生成SRT，推荐：tiny）
- `whisper.large_model`：大模型（用于生成最终TXT，推荐：large-v3）
- `whisper.device`：设备类型（cpu或cuda）
- `llm.api_key`：通义千问API密钥
- `llm.model`：大模型名称（推荐：qwen-plus）
- `paths.*`：各种文件路径配置

## 处理记录

工作流会自动维护两个记录文件：

1. **`data/downloaded_episodes.json`**：记录已下载的episode
2. **`data/processed_episodes.json`**：记录已处理完成的episode

已处理的episode会自动跳过，避免重复处理。

## 定时任务

使用cron定时运行：
```bash
# 每天上午9点检查新episode
0 9 * * * cd /path/to/podcast && python test_workflow.py

# 每天上午9点和下午6点各检查一次
0 9,18 * * * cd /path/to/podcast && python test_workflow.py
```

## 注意事项

1. **首次运行**：需要下载Whisper模型，可能需要一些时间
2. **API密钥**：确保在`config.yaml`中正确配置通义千问API密钥
3. **磁盘空间**：确保有足够的磁盘空间存储音频和转录文件
4. **处理时间**：处理时间取决于音频长度和模型大小，大模型处理时间较长
5. **已处理跳过**：工作流会自动跳过已处理的episode，如需重新处理，请删除对应的记录文件

## 故障排除

- **FFmpeg未找到**：确保FFmpeg已安装并在PATH中
- **Whisper模型下载失败**：检查网络连接，或手动下载模型
- **API调用失败**：检查API密钥是否正确，账户余额是否充足
- **文件路径错误**：检查`config.yaml`中的路径配置是否正确

