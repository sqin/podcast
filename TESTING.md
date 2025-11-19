# 测试说明

本目录包含多个测试脚本，用于测试播客工作流的各个功能模块。

## 测试脚本

### 1. `test_workflow.py` - 完整工作流测试
测试整个工作流：RSS下载 → Whisper生成 → 大模型处理

```bash
python test_workflow.py
```

**功能：**
- 自动检查今天是否有新episode
- 下载MP3文件
- 使用Whisper生成SRT和TXT文件
- 使用大模型识别广告时间段
- 使用大模型处理转录文本（翻译、分段、添加人名）

### 2. `test_rss_only.py` - RSS下载测试
单独测试RSS feed解析和MP3下载功能

```bash
python test_rss_only.py
```

**功能：**
- 解析RSS feed
- 检查今天是否有新episode
- 下载MP3文件到 `data/raw/` 目录
- 显示episode信息

### 3. `test_whisper_only.py` - Whisper生成测试
单独测试Whisper语音转录功能

```bash
python test_whisper_only.py
```

**功能：**
- 从 `data/raw/` 目录查找MP3文件
- 使用small/tiny模型生成SRT字幕文件
- 使用large/small模型生成TXT转录文件
- 输出文件保存到 `transcripts/` 目录

**注意：** 需要先有MP3文件，可以运行 `test_rss_only.py` 下载

### 4. `test_llm_only.py` - 大模型处理测试
单独测试大模型处理功能

```bash
python test_llm_only.py
```

**功能：**
- 从 `transcripts/srt/` 目录读取SRT文件
- 使用通义千问API识别广告时间段
- 从 `transcripts/txt/` 目录读取TXT文件
- 使用通义千问API处理转录文本（翻译、分段、添加人名）
- 输出文件保存到 `outputs/` 目录

**注意：** 需要先有SRT和TXT文件，可以运行 `test_whisper_only.py` 生成

## 测试顺序

推荐按以下顺序进行测试：

1. **第一步：测试RSS下载**
   ```bash
   python test_rss_only.py
   ```
   确保能成功下载MP3文件

2. **第二步：测试Whisper生成**
   ```bash
   python test_whisper_only.py
   ```
   确保能成功生成SRT和TXT文件

3. **第三步：测试大模型处理**
   ```bash
   python test_llm_only.py
   ```
   确保能成功识别广告和处理内容

4. **完整测试：运行完整工作流**
   ```bash
   python test_workflow.py
   ```
   测试整个流程是否顺畅

## 配置文件

测试前请确保 `config.yaml` 已正确配置：

- **RSS feed URL**: 已设置
- **Whisper模型**: 根据你的硬件选择（CPU建议使用tiny/small）
- **大模型API密钥**: 填入你的通义千问API密钥
- **路径配置**: 确保所有路径正确

## 常见问题

### 1. RSS下载失败
- 检查网络连接
- 确认RSS feed URL是否正确
- 检查今天是否有新episode（可以查看最新episode的发布日期）

### 2. Whisper生成很慢
- 如果使用CPU，建议使用tiny或small模型
- 如果有GPU，可以设置 `device: "cuda"`
- 音频文件越大，处理时间越长

### 3. 大模型API调用失败
- 检查API密钥是否正确
- 检查网络连接（需要能访问通义千问API）
- 确认模型名称是否正确（如 `qwen-turbo`, `qwen-plus` 等）

### 4. 找不到文件
- 确保已运行前置步骤（如测试Whisper前需要先有MP3文件）
- 检查文件路径配置是否正确
- 查看日志文件了解详细错误信息

## 输出文件位置

- **MP3文件**: `data/raw/`
- **SRT文件**: `transcripts/srt/`
- **TXT文件**: `transcripts/txt/`
- **处理后的内容**: `outputs/`
- **日志文件**: `logs/workflow.log`

