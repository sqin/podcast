# RSS下载功能使用说明

## 新功能特性

1. **不依赖时间检查** - 不再检查episode是否是今天的，可以下载任意episode
2. **指定下载数量** - 可以传递参数指定要下载多少个新episode
3. **自动去重** - 使用本地JSON文件记录已下载的episode，自动跳过已下载的

## 记录文件

下载记录保存在 `data/downloaded_episodes.json` 文件中，格式如下：

```json
{
  "episode_id_1": {
    "title": "Episode Title",
    "published": "2025-11-19 06:00:00",
    "mp3_path": "data/raw/Episode_Title.mp3",
    "downloaded_at": "2025-11-19T10:30:00"
  },
  ...
}
```

## 使用方法

### 1. 在代码中使用

```python
from src.rss_parser import RSSParser
from src.utils import load_config

config = load_config()
parser = RSSParser(
    feed_url=config['rss']['feed_url'],
    download_dir=config['paths']['raw_audio'],
    record_file=config['paths']['download_record']
)

# 下载3个新episode（跳过已下载的）
episodes = parser.download_episodes(count=3)

for episode in episodes:
    print(f"下载: {episode['title']}")
    print(f"路径: {episode['mp3_path']}")
```

### 2. 使用测试脚本

#### 下载1个episode（默认）
```bash
python test_rss_only.py
```

#### 下载多个episode
```bash
python test_rss_only.py -n 5    # 下载5个
python test_rss_only.py --count 10  # 下载10个
```

### 3. 在完整工作流中使用

```bash
# 下载1个episode并处理
python test_workflow.py

# 下载3个episode并处理
python test_workflow.py -n 3
```

## API说明

### RSSParser类

#### `__init__(feed_url, download_dir="data/raw", record_file="data/downloaded_episodes.json")`
初始化RSS解析器
- `feed_url`: RSS feed URL
- `download_dir`: MP3文件下载目录
- `record_file`: 下载记录文件路径

#### `download_episodes(count=1)`
下载指定数量的新episode
- `count`: 要下载的episode数量（默认: 1）
- 返回: 下载的episode列表，每个元素包含 `title`, `pub_date`, `mp3_path`, `episode`

#### `is_episode_downloaded(episode)`
检查episode是否已下载
- `episode`: episode对象
- 返回: `True` 如果已下载，`False` 如果未下载

#### `get_all_episodes(limit=None)`
获取所有episode列表
- `limit`: 限制返回数量（可选）
- 返回: episode列表

#### `get_latest_episode()`
获取最新的episode
- 返回: 最新的episode对象或None

## 示例

### 示例1: 下载最新5个未下载的episode

```python
from src.rss_parser import RSSParser
from src.utils import load_config

config = load_config()
parser = RSSParser(
    feed_url=config['rss']['feed_url'],
    download_dir=config['paths']['raw_audio']
)

# 下载5个新episode
episodes = parser.download_episodes(count=5)

print(f"成功下载 {len(episodes)} 个episode")
for ep in episodes:
    print(f"  - {ep['title']}")
```

### 示例2: 检查特定episode是否已下载

```python
from src.rss_parser import RSSParser

parser = RSSParser(feed_url="https://feeds.megaphone.fm/allearsenglish")
latest = parser.get_latest_episode()

if latest:
    if parser.is_episode_downloaded(latest):
        print(f"'{latest.get('title')}' 已下载")
    else:
        print(f"'{latest.get('title')}' 未下载")
```

### 示例3: 查看已下载记录

```python
from src.rss_parser import RSSParser

parser = RSSParser(feed_url="https://feeds.megaphone.fm/allearsenglish")

print(f"已下载 {len(parser.downloaded_episodes)} 个episode")
for ep_id, record in parser.downloaded_episodes.items():
    print(f"  - {record['title']} ({record['published']})")
```

## 注意事项

1. **记录文件格式**: 记录文件使用JSON格式，如果文件损坏，程序会自动创建新文件
2. **Episode标识**: 使用episode的guid或link作为唯一标识，如果没有则使用title+pubDate组合
3. **文件去重**: 即使记录文件丢失，如果MP3文件已存在，也不会重复下载
4. **下载顺序**: 按照RSS feed中的顺序下载（最新的在前）

## 故障排除

### 问题1: 记录文件损坏
**解决**: 删除 `data/downloaded_episodes.json` 文件，程序会自动创建新文件

### 问题2: 想重新下载某个episode
**解决**: 
1. 从记录文件中删除对应的条目
2. 或删除对应的MP3文件
3. 重新运行下载

### 问题3: 下载数量不足
**可能原因**: 
- RSS feed中的episode数量少于请求的数量
- 所有episode都已下载

**解决**: 检查RSS feed或查看日志输出

