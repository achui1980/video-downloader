# AGENTS.md - YouTube Video Downloader 项目指南

## 项目概述

这是一个基于 Python 3.12+ 和 PyQt6 的 YouTube 视频下载桌面应用程序，主要功能包括：

- **视频下载**：支持多种格式（最佳质量、仅视频、仅音频MP3、1080p/720p/480p/360p）
- **字幕管理**：下载、合并、AI翻译（SRT格式）、Whisper语音识别生成字幕
- **浏览器插件**：Chrome扩展，可通过右键菜单快速下载视频
- **下载管理**：多任务并发下载、进度跟踪、速度限制、代理支持
- **历史记录**：JSON持久化的下载历史，支持CSV导出
- **API服务**：FastAPI服务器（端口8765），供浏览器插件调用

### 技术栈

| 组件 | 技术 |
|------|------|
| GUI框架 | PyQt6 + QSS样式 |
| 下载引擎 | yt-dlp |
| API服务 | FastAPI + Uvicorn |
| AI翻译 | OpenAI SDK (兼容DeepSeek/ModelScope) |
| 语音识别 | Whisper |
| 日志 | Loguru |
| 构建 | PyInstaller |

### 项目结构

```
video-downloader/
├── main.py                    # 应用程序入口
├── ui.py                      # 主窗口UI实现 (YoutubeDownloader)
├── api_server.py              # FastAPI服务器 (浏览器插件通信)
├── download_manager.py         # 下载配置管理 (单例模式)
├── download_thread.py          # 下载/分析线程 (QThread)
├── ai_translator.py           # AI字幕翻译 (流式响应)
├── whisper_service.py         # Whisper语音识别服务
├── subtitle_merger.py         # FFmpeg字幕合成
├── history_manager.py         # 历史记录JSON持久化
├── config.py                  # 配置管理 (JSON)
├── styles.py                  # QSS深色主题样式
├── utils.py                   # 工具函数
├── my_logger.py               # 日志封装
├── custom_events.py           # 自定义Qt事件
├── task_widget.py             # 下载任务UI组件
├── tabs/                      # UI标签页
│   ├── history_tab.py         # 历史记录标签
│   └── settings_tab.py        # 设置标签
└── chrome-plugin/             # Chrome扩展 (Manifest V3)
```

## 运行命令

### 启动应用

```bash
# 开发模式运行主应用
python main.py

# 启动API服务器（供浏览器插件使用）
python api_server.py
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 构建可执行文件

```bash
# 使用PyInstaller打包
python build_exe.py

# 打包后可执行文件位于 dist/ 目录
```

## 代码规范

### 文件头部

每个Python文件应包含标准头部：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```

### 导入顺序

1. 标准库 (`import os`, `import sys`, `from datetime import datetime`)
2. 第三方库 (`import yt_dlp`, `from PyQt6.QtWidgets import ...`, `from fastapi import ...`)
3. 本地模块 (`from download_manager import DownloadManager`, `from utils import ...`)

分组之间用空行分隔，按字母排序：

```python
import os
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
import yt_dlp

from config import Config
from download_manager import DownloadManager
from utils import format_duration, format_size
```

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | CamelCase | `class YoutubeDownloader`, `class DownloadManager` |
| 函数/变量 | snake_case | `def start_download()`, `download_path` |
| 常量 | UPPER_SNAKE_CASE | `DEFAULT_FORMAT`, `API_PORT` |
| Qt信号 | snake_case | `progress_signal`, `complete_signal` |
| Qt槽函数 | snake_case | `def on_download_complete()` |
| 私有成员 | _前缀 | `self._instance`, `self._tasks` |

### 类型注解

使用类型注解提高代码可读性：

```python
def format_duration(seconds: int | float) -> str:
    """格式化视频时长"""
    if not seconds:
        return "未知"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

class DownloadRequest(BaseModel):
    url: str
    format: str = Config.DEFAULT_FORMAT
    subtitle: bool = False
```

### Qt信号定义

```python
from PyQt6.QtCore import QThread, pyqtSignal

class DownloadThread(QThread):
    progress_signal = pyqtSignal(dict)
    complete_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal()
```

### 错误处理

使用try/except捕获具体异常，避免裸except：

```python
# 好的实践
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        saved_settings = json.load(f)
except FileNotFoundError:
    # 文件不存在，使用默认值
    pass
except json.JSONDecodeError as e:
    print(f"配置文件格式错误: {e}")
except Exception as e:
    print(f"加载配置时出错: {e}")

# yt-dlp错误处理
try:
    info = ydl.extract_info(url, download=False)
except yt_dlp.utils.DownloadError as e:
    error_msg = str(e)
    if "Private video" in error_msg:
        raise Exception("无法下载：这是一个私有视频")
    elif "Sign in" in error_msg:
        raise Exception("无法下载：需要登录才能观看")
    else:
        raise Exception(f"下载错误: {error_msg}")
```

### Qt线程模式

使用QThread处理后台任务，避免阻塞UI：

```python
class DownloadThread(QThread):
    progress_signal = pyqtSignal(dict)
    complete_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, options):
        super().__init__()
        self.url = url
        self.options = options
        self.is_cancelled = False
        
    def run(self):
        try:
            self.ydl = yt_dlp.YoutubeDL(self.options)
            info = self.ydl.extract_info(self.url, download=True)
            self.complete_signal.emit(info)
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True
```

### 配置管理

使用Config类统一管理配置，JSON持久化：

```python
class Config:
    DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Movies/yt-dlp")
    APP_WINDOW_TITLE = 'YouTube 视频下载器'
    
    settings = {
        "subtitle": {"enabled": False, "language": "自动"},
        "ai_translator": {"api_key": "", "base_url": "", "model": ""},
    }
    
    @classmethod
    def load_config(cls):
        config_path = cls.get_config_path()
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cls.settings = json.load(f)
    
    @classmethod
    def save_config(cls):
        with open(cls.get_config_path(), 'w', encoding='utf-8') as f:
            json.dump(cls.settings, f, indent=4, ensure_ascii=False)
```

### 单例模式

DownloadManager等核心类使用单例模式：

```python
class DownloadManager:
    _instance = None
    
    def __init__(self):
        self.tasks = {}
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

### API响应模型

使用Pydantic BaseModel定义请求/响应：

```python
from pydantic import BaseModel
from typing import Optional

class DownloadRequest(BaseModel):
    url: str
    format: str = Config.DEFAULT_FORMAT
    output_dir: Optional[str] = None
    subtitle: bool = False

class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str
    file_path: Optional[str] = None
```

### UI样式

使用QSS定义深色主题样式，在styles.py中集中管理：

```python
class Styles:
    DARK_THEME = """
    QMainWindow, QWidget#MainContent {
        background-color: #1e1e1e;
        color: #cccccc;
    }
    QPushButton.PrimaryBtn {
        background-color: #007acc;
        color: white;
        font-weight: 600;
    }
    """
```

### 日志使用

使用Loguru进行日志记录：

```python
from my_logger import MyLogger

logger = MyLogger.get_instance(log_file)
logger.info(f"下载开始: {url}")
logger.error(f"下载失败: {error}")
```

## 注意事项

1. **API Key安全**：配置中的API Key应避免提交到git仓库，已在.gitignore中忽略config.json
2. **资源路径**：使用`resource_path()`函数处理PyInstaller打包后的资源路径
3. **线程安全**：UI操作必须在主线程，QThread用于后台任务
4. **文件编码**：所有文件操作使用UTF-8编码
5. **依赖版本**：Python 3.12+, PyQt6>=6.8.1, yt-dlp>=2026.3.17
