# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DownloadOptions:
    """一次下载任务的全部参数（由 ui.py 从页面+设置组装，传给 controller）"""
    url: str
    format: str
    download_path: str
    subtitle: Optional[dict] = None
    proxy: Optional[str] = None
    speed_limit: Optional[str] = None
    use_chrome_cookies: bool = False


@dataclass
class DownloadSettings:
    """设置页快照，替代 ui.py 直接读 settings_tab 控件"""
    subtitle_enabled: bool = False
    subtitle_language: str = "自动"
    only_langs: List[str] = field(default_factory=lambda: ["zh-Hans"])
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""
    ai_batch_size: int = 200
    proxy_enabled: bool = False
    proxy_url: str = ""
    limit_speed: bool = False
    limit_rate: str = ""
    chrome_cookies: bool = False
