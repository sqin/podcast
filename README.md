# 播客自动发布工作流

自动化的播客处理工作流，从RSS feed解析到微信公众号发布。

## 功能特性

- 自动检测RSS feed中的新episode
- 使用Whisper进行语音转录（small模型生成SRT，large-v3生成TXT）
- 基于大模型识别广告时间段
- 使用FFmpeg去除广告片段
- 使用通义千问进行内容翻译和格式化
- 自动发布到微信公众号

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
```

3. 配置`config.yaml`文件，填入你的API密钥和配置信息

## 使用方法

运行主工作流：
```bash
python main.py
```

## 项目结构

```
podcast/
├── main.py                 # 主工作流入口
├── config.yaml            # 配置文件
├── requirements.txt       # Python依赖
├── src/                   # 源代码模块
├── data/                  # 音频文件
├── transcripts/           # 转录文件
└── outputs/               # 输出文件
```

## 定时任务

使用cron定时运行：
```bash
# 每天上午9点和下午6点检查新episode
0 9,18 * * * cd /path/to/podcast && python main.py
```

