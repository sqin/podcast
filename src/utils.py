"""工具函数模块"""
import os
import logging
from datetime import datetime, timezone
from dateutil import parser as date_parser
from pathlib import Path
import yaml


def setup_logging(log_level="INFO", log_file=None):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            *([logging.FileHandler(log_file)] if log_file else [])
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_path="config.yaml"):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_dir(path):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def is_today(date_str):
    """检查日期字符串是否为今天"""
    try:
        # 解析RSS日期字符串
        date_obj = date_parser.parse(date_str)
        
        # 转换为UTC时间（如果原时间没有时区信息，假设为UTC）
        if date_obj.tzinfo is None:
            date_obj = date_obj.replace(tzinfo=timezone.utc)
        
        # 获取今天的日期（UTC）
        today = datetime.now(timezone.utc).date()
        
        # 比较日期部分
        return date_obj.date() == today
    except Exception as e:
        logging.error(f"日期解析错误: {e}, 日期字符串: {date_str}")
        return False


def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

