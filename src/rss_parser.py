"""RSS feed解析和MP3下载模块"""
import feedparser
import requests
import logging
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from .utils import ensure_dir, sanitize_filename

logger = logging.getLogger(__name__)


class RSSParser:
    """RSS解析器"""
    
    def __init__(self, feed_url, download_dir="data/raw", record_file="data/downloaded_episodes.json"):
        self.feed_url = feed_url
        self.download_dir = ensure_dir(download_dir)
        self.record_file = Path(record_file)
        self.downloaded_episodes = self._load_downloaded_episodes()
    
    def parse_feed(self):
        """解析RSS feed"""
        try:
            logger.info(f"正在解析RSS feed: {self.feed_url}")
            feed = feedparser.parse(self.feed_url)
            
            if feed.bozo:
                logger.warning(f"RSS feed解析警告: {feed.bozo_exception}")
            
            return feed
        except Exception as e:
            logger.error(f"RSS feed解析失败: {e}")
            raise
    
    def get_all_episodes(self, limit=None):
        """获取所有episode列表"""
        feed = self.parse_feed()
        
        if not feed.entries:
            logger.warning("RSS feed中没有找到episode")
            return []
        
        episodes = feed.entries
        if limit:
            episodes = episodes[:limit]
        
        logger.info(f"找到 {len(episodes)} 个episode")
        return episodes
    
    def get_latest_episode(self):
        """获取最新的episode"""
        episodes = self.get_all_episodes(limit=1)
        if episodes:
            return episodes[0]
        return None
    
    def _load_downloaded_episodes(self):
        """加载已下载的episode记录"""
        if not self.record_file.exists():
            logger.info(f"记录文件不存在，创建新文件: {self.record_file}")
            self.record_file.parent.mkdir(parents=True, exist_ok=True)
            return {}
        
        try:
            with open(self.record_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            logger.info(f"加载了 {len(records)} 条已下载记录")
            return records
        except Exception as e:
            logger.warning(f"加载记录文件失败: {e}，将创建新记录")
            return {}
    
    def _save_downloaded_episodes(self):
        """保存已下载的episode记录"""
        try:
            self.record_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.record_file, 'w', encoding='utf-8') as f:
                json.dump(self.downloaded_episodes, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存 {len(self.downloaded_episodes)} 条下载记录")
        except Exception as e:
            logger.error(f"保存记录文件失败: {e}")
    
    def _get_episode_id(self, episode):
        """获取episode的唯一标识符"""
        # 优先使用guid，如果没有则使用link
        guid = episode.get('id') or episode.get('guid', '')
        if guid:
            return str(guid)
        
        link = episode.get('link', '')
        if link:
            return link
        
        # 如果都没有，使用title和pubDate组合
        title = episode.get('title', '')
        pub_date = episode.get('published', '')
        return f"{title}_{pub_date}"
    
    def is_episode_downloaded(self, episode):
        """检查episode是否已下载"""
        episode_id = self._get_episode_id(episode)
        return episode_id in self.downloaded_episodes
    
    def _record_downloaded_episode(self, episode, mp3_path):
        """记录已下载的episode"""
        episode_id = self._get_episode_id(episode)
        self.downloaded_episodes[episode_id] = {
            'title': episode.get('title', 'Unknown'),
            'published': episode.get('published', ''),
            'mp3_path': mp3_path,
            'downloaded_at': datetime.now().isoformat()
        }
        self._save_downloaded_episodes()
    
    def get_mp3_url(self, episode):
        """从episode中获取MP3下载URL"""
        # 检查enclosures
        if hasattr(episode, 'enclosures') and episode.enclosures:
            for enclosure in episode.enclosures:
                if enclosure.get('type', '').startswith('audio'):
                    url = enclosure.get('href', '')
                    if url:
                        logger.info(f"找到MP3 URL: {url}")
                        return url
        
        # 如果没有找到，尝试从links中查找
        if hasattr(episode, 'links') and episode.links:
            for link in episode.links:
                if link.get('type', '').startswith('audio'):
                    url = link.get('href', '')
                    if url:
                        logger.info(f"从links中找到MP3 URL: {url}")
                        return url
        
        logger.error("未找到MP3下载URL")
        return None
    
    def download_mp3(self, url, filename=None):
        """下载MP3文件"""
        try:
            if not filename:
                # 从URL中提取文件名
                parsed_url = urlparse(url)
                filename = Path(parsed_url.path).name
                if not filename or not filename.endswith('.mp3'):
                    filename = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            
            # 清理文件名
            filename = sanitize_filename(filename)
            filepath = Path(self.download_dir) / filename
            
            # 如果文件已存在，跳过下载
            if filepath.exists():
                logger.info(f"文件已存在，跳过下载: {filepath}")
                return str(filepath)
            
            logger.info(f"开始下载MP3: {url} -> {filepath}")
            
            # 下载文件
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 保存文件
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"MP3下载完成: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"MP3下载失败: {e}")
            raise
    
    def download_episodes(self, count=1):
        """下载指定数量的新episode（跳过已下载的）"""
        logger.info(f"开始下载 {count} 个新episode")
        
        # 获取所有episode
        all_episodes = self.get_all_episodes()
        
        if not all_episodes:
            logger.warning("没有找到任何episode")
            return []
        
        downloaded_list = []
        skipped_count = 0
        
        for episode in all_episodes:
            if len(downloaded_list) >= count:
                break
            
            # 检查是否已下载
            if self.is_episode_downloaded(episode):
                skipped_count += 1
                title = episode.get('title', 'Unknown')
                logger.info(f"跳过已下载的episode: {title}")
                continue
            
            # 下载episode
            try:
                episode_data = self._download_single_episode(episode)
                if episode_data:
                    downloaded_list.append(episode_data)
                    logger.info(f"成功下载 ({len(downloaded_list)}/{count}): {episode_data['title']}")
            except Exception as e:
                logger.error(f"下载episode失败: {e}")
                continue
        
        logger.info(f"下载完成: 成功 {len(downloaded_list)} 个，跳过 {skipped_count} 个")
        return downloaded_list
    
    def _download_single_episode(self, episode):
        """下载单个episode"""
        # 获取episode信息
        title = episode.get('title', 'Unknown')
        pub_date = episode.get('published', '')
        
        # 获取并下载MP3
        mp3_url = self.get_mp3_url(episode)
        if not mp3_url:
            logger.error(f"无法获取MP3 URL: {title}")
            return None
        
        # 生成文件名
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}.mp3"
        
        mp3_path = self.download_mp3(mp3_url, filename)
        
        # 记录已下载
        self._record_downloaded_episode(episode, mp3_path)
        
        return {
            'title': title,
            'pub_date': pub_date,
            'mp3_path': mp3_path,
            'episode': episode
        }
    
    def process_today_episode(self):
        """处理今天的新episode：检查、下载并返回元数据（保留向后兼容）"""
        # 下载1个新episode
        episodes = self.download_episodes(count=1)
        if episodes:
            return episodes[0]
        return None

