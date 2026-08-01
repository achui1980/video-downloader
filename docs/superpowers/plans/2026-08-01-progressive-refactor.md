# 渐进式解耦重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变外部行为的前提下，拆分 `ui.py` 上帝类、统一线程模型、清理技术债。

**Architecture:** 新增 `pages/`（页面模块）、`download_controller.py`（下载编排）、`download_worker.py`（纯 Python 下载 worker）、`constants.py`（共享常量）、`download_options.py`（dataclass）。`ui.py` 瘦身为纯装配。`api_server.py` 不再用 QThread 和忙轮询。

**Tech Stack:** Python 3.12+、PyQt6、yt-dlp、FastAPI

**验证约定（替代 TDD，因项目无测试套件且 spec 明确不引入测试框架）:** 每个任务用 `python -m py_compile <touched .py files>` 验证语法 + 合理分组后冒烟。每个任务单次提交。

**关键不变量（不得违反）：**
- API 路由：`POST /api/v1/download`、`GET /api/v1/status/{task_id}`、`DELETE /api/v1/download/{task_id}` 不变
- `chrome-plugin/` 三个文件不改
- 历史文件 `~/youtube_downloader_history.json` 读写格式不变
- 下载产物文件名/目录逻辑不变

---

### Task 1: 共享常量与配置清理

**Files:**
- Create: `constants.py`
- Modify: `config.py`, `config.json`, `utils.py`
- Delete: `history.json`

- [ ] **Step 1: 创建 `constants.py`**

```python
# -*- coding: utf-8 -*-

FORMAT_OPTIONS = [
    "最佳质量",
    "仅视频",
    "仅音频 (MP3)",
    "仅字幕",
    "1080p",
    "720p",
    "480p",
    "360p",
]

DEFAULT_FORMAT = FORMAT_OPTIONS[0]

SUBTITLE_LANGUAGES = ["自动", "中文", "英文", "日文"]

LANGUAGE_CODES = {
    "中文": "zh-Hans",
    "英文": "en",
    "日文": "ja",
}
```

- [ ] **Step 2: 修改 `config.py`，引用常量并移除真实 API Key**

修改 `config.py`：

```python
import os
import json
from constants import DEFAULT_FORMAT

class Config:
    # 路径配置
    DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Movies/yt-dlp")
    DEFAULT_LOG_DIR_NAME = 'logs'
    CONFIG_FILE_NAME = 'config.json'

    # UI 默认值
    DEFAULT_VIDEO_URL = "https://www.youtube.com/shorts/RIrEOv7sXYo"
    APP_WINDOW_TITLE = 'YouTube 视频下载器'
    APP_WINDOW_SIZE = (900, 600)

    # API 配置
    API_HOST = "127.0.0.1"
    API_PORT = 8765

    # 下载配置
    DEFAULT_FORMAT = DEFAULT_FORMAT
    DEFAULT_SYSTEM = "Mac OS"
```

然后把 `settings` 字典里 `"api_key": "ms-<redacted>"` 改为 `"api_key": ""`。其余代码（`get_log_dir`/`ensure_dirs`/`get_config_path`/`load_config`/`save_config`/`_merge_dict`）保持不变。

- [ ] **Step 3: 修改 `config.json`，把真实 API Key 替换为占位符**

把 `config.json` 中 `"api_key": "ms-<redacted>"` 改为 `"api_key": ""`。

- [ ] **Step 4: 修改 `utils.py` 使用共享常量**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from constants import LANGUAGE_CODES

def format_duration(seconds):
    """格式化视频时长"""
    if not seconds:
        return "未知"

    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    else:
        return f"{m}:{s:02d}"

def format_size(bytes):
    """格式化文件大小"""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024):.1f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.1f} GB"

def format_time(seconds):
    """将秒数格式化为时分秒格式，精确到秒"""
    seconds = int(seconds)

    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}分{s}秒"
    else:
        h, remainder = divmod(seconds, 3600)
        m, s = divmod(remainder, 60)
        return f"{h}时{m}分{s}秒"

def get_language_code(language_name):
    """将语言名称转换为语言代码"""
    return LANGUAGE_CODES.get(language_name, None)
```

- [ ] **Step 5: 删除空的 `history.json`**

```bash
rm history.json
```

- [ ] **Step 6: 验证并提交**

```bash
python -m py_compile constants.py config.py utils.py
git add constants.py config.py config.json utils.py && git rm --quiet history.json
git commit -m "refactor: 提取共享常量，清理提交的真实 API Key"
```

---

### Task 2: 下载选项/设置 dataclass

**Files:**
- Create: `download_options.py`

- [ ] **Step 1: 创建 `download_options.py`**

```python
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
```

- [ ] **Step 2: 验证并提交**

```bash
python -m py_compile download_options.py
git add download_options.py && git commit -m "refactor: 新增 DownloadOptions/DownloadSettings dataclass"
```

---

### Task 3: 纯 Python 下载 worker

**Files:**
- Create: `download_worker.py`

- [ ] **Step 1: 创建 `download_worker.py`**

```python
# -*- coding: utf-8 -*-

import threading
import yt_dlp


class DownloadCancelled(Exception):
    """内部取消信号，非 yt-dlp 异常"""
    pass


class DownloadWorker:
    """纯 Python 下载 worker，无 Qt 依赖。GUI 用 DownloadThread 包装，API 服务直接使用。"""

    def __init__(self, url, options, on_progress=None, on_complete=None, on_error=None):
        self.url = url
        self.options = dict(options)
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self._cancelled = threading.Event()
        self.done = threading.Event()
        self.ydl = None

    def cancel(self):
        """请求取消下载"""
        self._cancelled.set()

    @property
    def cancelled(self):
        return self._cancelled.is_set()

    def _progress_hook(self, d):
        if self._cancelled.is_set():
            raise yt_dlp.utils.DownloadCancelled("下载已取消")
        if d["status"] == "downloading" and self.on_progress:
            self.on_progress(d)

    def run(self):
        try:
            if self._cancelled.is_set():
                raise DownloadCancelled("下载已取消")

            self.options["progress_hooks"] = [self._progress_hook]
            self.ydl = yt_dlp.YoutubeDL(self.options)
            info = self.ydl.extract_info(self.url, download=True)

            if self._cancelled.is_set():
                raise DownloadCancelled("下载已取消")

            if self.on_complete:
                self.on_complete(info)
        except (DownloadCancelled, yt_dlp.utils.DownloadCancelled):
            if self.on_error:
                self.on_error("cancelled")
        except Exception as e:
            if self._cancelled.is_set():
                if self.on_error:
                    self.on_error("cancelled")
            elif self.on_error:
                self.on_error(str(e))
        finally:
            self.done.set()
```

- [ ] **Step 2: 验证并提交**

```bash
python -m py_compile download_worker.py
git add download_worker.py && git commit -m "refactor: 新增纯 Python 下载 worker"
```

---

### Task 4: 重写 `download_thread.py` 为 worker 薄封装

**Files:**
- Rewrite: `download_thread.py`

- [ ] **Step 1: 整体重写 `download_thread.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal

from download_manager import DownloadManager
from download_worker import DownloadWorker


class DownloadThread(QThread):
    progress_signal = pyqtSignal(dict)
    complete_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal()

    def __init__(self, url, options):
        super().__init__()
        self.worker = DownloadWorker(
            url,
            options,
            on_progress=self.progress_signal.emit,
            on_complete=self.complete_signal.emit,
            on_error=self._on_worker_error,
        )

    def run(self):
        self.worker.run()

    def _on_worker_error(self, message):
        if message == "cancelled":
            self.cancelled_signal.emit()
        else:
            self.error_signal.emit(message)

    def cancel(self):
        self.worker.cancel()


class AnalyzeThread(QThread):
    info_ready_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, parent, url, ydl_opts=None):
        super().__init__(parent)
        self.url = url
        self.ydl_opts = ydl_opts or {}

    def run(self):
        try:
            self.status_signal.emit("正在获取视频信息...")
            info = DownloadManager.extract_info(self.url, self.ydl_opts, download=False)
            self.info_ready_signal.emit(info)
        except Exception as e:
            self.error_signal.emit(f"分析视频时出错: {str(e)}")
```

注意：此文件不再引用 `custom_events`，`cancel()` 不再调用 yt-dlp 私有 API `_finish_multiline_status`。

- [ ] **Step 2: 验证并提交**

```bash
python -m py_compile download_thread.py
git add download_thread.py && git commit -m "refactor: DownloadThread 改为包装 DownloadWorker，移除私有 API 依赖"
```

---

### Task 5: 修复 `download_manager.py` 裸 except

**Files:**
- Modify: `download_manager.py:66-70`

- [ ] **Step 1: 修复创建日志目录处的裸 except**

把 `download_manager.py` 中：

```python
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except:
                pass
```

改为：

```python
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"创建日志目录失败 {log_dir}: {e}")
```

其余逻辑（`prepare_download_options` 的格式 if/elif、`extract_info`、`get_download_info_from_result`、`get_video_summary`、`DownloadManager` 单例/任务管理）保持不变。

- [ ] **Step 2: 验证并提交**

```bash
python -m py_compile download_manager.py
git add download_manager.py && git commit -m "refactor: 修复 prepare_download_options 裸 except"
```

---

### Task 6: 修复 `ai_translator.py` 重复 except + SettingsTab 设置快照

**Files:**
- Modify: `ai_translator.py:50-56`
- Modify: `tabs/settings_tab.py`

- [ ] **Step 1: 修复 `ai_translator.py` 重复的 except**

把 `ai_translator.py` 中 `translate_batch_stream` 末尾两段几乎相同的 `except Exception` 合并为一段：

```python
        except Exception as e:
            print(f"Translation error: {e}")
            raise e
```

即删除文件中重复出现的第二个 `except Exception as e:` 块（该函数只保留一个 except）。其余文件内容不变。

- [ ] **Step 2: 给 `SettingsTab` 增加 `get_settings()`**

在 `tabs/settings_tab.py` 顶部导入后（紧跟 `from config import Config` 之后）：

```python
from download_options import DownloadSettings
```

然后在 `setup_connections` 方法之前新增方法：

```python
    def get_settings(self) -> DownloadSettings:
        """读取当前 UI 值，返回设置快照。替代外部直接读控件。"""
        only_langs = []
        if self.zh_subtitle_check.isChecked():
            only_langs.append('zh-Hans')
        if self.en_subtitle_check.isChecked():
            only_langs.append('en')
        if self.jp_subtitle_check.isChecked():
            only_langs.append('ja')

        batch_size = 200
        try:
            batch_size = int(self.ai_batch_size.text().strip() or "200")
        except ValueError:
            batch_size = 200

        return DownloadSettings(
            subtitle_enabled=self.subtitle_check.isChecked(),
            subtitle_language=self.subtitle_lang_combo.currentText(),
            only_langs=only_langs,
            ai_api_key=self.ai_api_key.text().strip(),
            ai_base_url=self.ai_base_url.text().strip(),
            ai_model=self.ai_model.text().strip(),
            ai_batch_size=batch_size,
            proxy_enabled=self.proxy_check.isChecked(),
            proxy_url=self.proxy_input.text().strip(),
            limit_speed=self.limit_check.isChecked(),
            limit_rate=self.limit_input.text().strip(),
            chrome_cookies=self.chrome_cookies_check.isChecked(),
        )
```

`load_from_config`、`save_to_config`、`setup_connections` 保持不变。

- [ ] **Step 3: 验证并提交**

```bash
python -m py_compile ai_translator.py tabs/settings_tab.py
git add ai_translator.py tabs/settings_tab.py && git commit -m "refactor: 修复重复 except，SettingsTab 增加设置快照"
```

---

### Task 7: 页面模块 `pages/`

**Files:**
- Create: `pages/__init__.py`, `pages/tasks_page.py`, `pages/new_download_page.py`

- [ ] **Step 1: 创建 `pages/__init__.py`（空文件）**

```bash
touch pages/__init__.py
```

- [ ] **Step 2: 创建 `pages/tasks_page.py`**

```python
# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from task_widget import TaskWidget


class TasksPage(QWidget):
    """当前任务页：负责 TaskWidget 容器，不持有下载线程。"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("当前任务")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        self.tasks_container_layout = QVBoxLayout(scroll_content)
        self.tasks_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tasks_container_layout.setSpacing(10)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def add_task_widget(self, url) -> TaskWidget:
        widget = TaskWidget(url, title=f"正在解析: {url}")
        self.tasks_container_layout.addWidget(widget)
        return widget

    def remove_task_widget(self, widget: TaskWidget):
        self.tasks_container_layout.removeWidget(widget)
        widget.deleteLater()
```

- [ ] **Step 3: 创建 `pages/new_download_page.py`**

```python
# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFrame,
    QGridLayout,
    QFileDialog,
    QMessageBox,
    QApplication,
)

from config import Config
from constants import FORMAT_OPTIONS
from utils import format_duration


class NewDownloadPage(QWidget):
    """新建下载页：纯 UI 表面，通过信号上报意图，不碰设置页和其他页面。"""

    analyze_requested = pyqtSignal(str)  # url
    download_requested = pyqtSignal(str, str, str)  # url, format, download_path

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(20)

        title = QLabel("新建下载")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # 1. 视频链接卡片
        link_card = QFrame()
        link_card.setProperty("class", "Card")
        card_layout = QVBoxLayout(link_card)
        card_layout.addWidget(QLabel("视频链接", objectName="SectionTitle"))

        input_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "在此粘贴 YouTube 视频链接 (例如: https://www.youtube.com/watch?v=...)"
        )
        self.url_input.setMinimumHeight(45)
        input_row.addWidget(self.url_input)

        self.paste_btn = QPushButton("粘贴")
        self.paste_btn.setMinimumHeight(45)
        self.paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn.setToolTip("从剪切板粘贴链接")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        input_row.addWidget(self.paste_btn)

        self.analyze_btn = QPushButton("分析链接")
        self.analyze_btn.setMinimumHeight(45)
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self.request_analyze)
        input_row.addWidget(self.analyze_btn)

        card_layout.addLayout(input_row)
        layout.addWidget(link_card)

        # 2. 下载配置卡片
        config_card = QFrame()
        config_card.setProperty("class", "Card")
        config_layout = QVBoxLayout(config_card)
        config_layout.setSpacing(15)
        config_layout.addWidget(QLabel("下载配置", objectName="SectionTitle"))

        grid = QGridLayout()
        grid.setVerticalSpacing(15)
        grid.setHorizontalSpacing(20)

        grid.addWidget(QLabel("下载格式"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMAT_OPTIONS)
        grid.addWidget(self.format_combo, 0, 1)

        grid.addWidget(QLabel("保存位置"), 0, 2)
        path_row = QHBoxLayout()
        self.download_path = QLineEdit()
        self.download_path.setText(Config.DEFAULT_DOWNLOAD_PATH)
        path_row.addWidget(self.download_path)
        self.browse_btn = QPushButton("...")
        self.browse_btn.setFixedWidth(40)
        self.browse_btn.clicked.connect(self.browse_folder)
        path_row.addWidget(self.browse_btn)
        grid.addLayout(path_row, 0, 3)

        grid.addWidget(QLabel("系统平台"), 1, 0)
        self.system_combo = QComboBox()
        self.system_combo.addItems([Config.DEFAULT_SYSTEM, "Windows", "Linux"])
        self.system_combo.setCurrentText(Config.DEFAULT_SYSTEM)
        grid.addWidget(self.system_combo, 1, 1)

        config_layout.addLayout(grid)

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setProperty("class", "PrimaryBtn")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self.request_download)
        action_row.addWidget(self.download_btn)
        config_layout.addLayout(action_row)
        layout.addWidget(config_card)

        # 3. 视频信息预览区 (初始隐藏)
        self.video_info_card = QFrame()
        self.video_info_card.setProperty("class", "Card")
        self.video_info_card.setVisible(False)
        info_layout = QVBoxLayout(self.video_info_card)
        self.video_info_label = QLabel()
        info_layout.addWidget(self.video_info_label)
        layout.addWidget(self.video_info_card)

        layout.addStretch()

    # ---- 交互 ----

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.url_input.setText(text)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择下载文件夹", self.download_path.text()
        )
        if folder:
            self.download_path.setText(folder)

    def request_analyze(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return
        self.analyze_btn.setText("分析中...")
        self.analyze_btn.setEnabled(False)
        self.video_info_card.setVisible(True)
        self.video_info_label.setText("正在获取视频信息，请稍候...")
        self.analyze_requested.emit(url)

    def request_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return
        self.download_requested.emit(
            url, self.format_combo.currentText(), self.download_path.text()
        )

    # ---- 分析结果展示（由 ui.py 信号驱动）----

    def show_video_info(self, info):
        if not info:
            return
        info_text = f"<b>{info.get('title', '未知')}</b><br>"
        info_text += f"上传者: {info.get('uploader', '未知')} | "
        info_text += f"时长: {format_duration(info.get('duration', 0))} | "
        info_text += f"日期: {info.get('upload_date', '未知')}<br>"

        subtitles = info.get("subtitles", {})
        auto_captions = info.get("automatic_captions", {})

        all_langs = set()
        if subtitles:
            all_langs.update(subtitles.keys())
        if auto_captions:
            all_langs.update(auto_captions.keys())

        if all_langs:
            priority_langs = ["zh-Hans", "zh-Hant", "en", "ja", "ko"]
            display_langs = []
            for lang in priority_langs:
                if lang in all_langs:
                    display_langs.append(lang)
                    all_langs.remove(lang)
            sorted_remaining = sorted(list(all_langs))
            display_langs.extend(sorted_remaining[:5])
            langs_str = ", ".join(display_langs)
            if len(all_langs) > 5:
                langs_str += f" 等 {len(all_langs) + len(display_langs)} 种语言"
            info_text += f"支持字幕: {langs_str}"
        else:
            info_text += "支持字幕: 无"

        self.video_info_label.setText(info_text)
        self.video_info_card.setVisible(True)

    def show_analyze_error(self, message):
        self.video_info_label.setText(f"错误: {message}")

    def reset_analyze_btn(self):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("分析链接")
```

- [ ] **Step 4: 验证并提交**

```bash
python -m py_compile pages/__init__.py pages/tasks_page.py pages/new_download_page.py
git add pages/ && git commit -m "refactor: 新增页面模块 pages/，从 ui.py 拆出新建下载页与任务页"
```

---

### Task 8: 下载编排控制器

**Files:**
- Create: `download_controller.py`

- [ ] **Step 1: 创建 `download_controller.py`**

```python
# -*- coding: utf-8 -*-

import os

from PyQt6.QtCore import QObject, pyqtSignal

from download_manager import DownloadManager
from download_options import DownloadOptions
from download_thread import DownloadThread
from pages.tasks_page import TasksPage


class DownloadController(QObject):
    """下载编排：持有线程与 TaskWidget，通过信号向上层（ui.py）汇报。"""

    active_count_changed = pyqtSignal(int)
    history_item_completed = pyqtSignal(dict, str)  # info, format_option

    def __init__(self, tasks_page: TasksPage, parent=None):
        super().__init__(parent)
        self.tasks_page = tasks_page
        self.download_threads = {}
        self.active_tasks = {}

    def has_active(self, url) -> bool:
        return url in self.download_threads

    def start(self, options: DownloadOptions):
        url = options.url
        if url in self.download_threads:
            self._cancel_existing(url)

        ydl_opts = DownloadManager.prepare_download_options(
            options.format,
            options.download_path,
            options.subtitle,
            options.speed_limit,
            options.proxy,
            options.use_chrome_cookies,
            enable_logging=True,
            url=url,
        )

        task_widget = self.tasks_page.add_task_widget(url)
        self.active_tasks[url] = task_widget

        thread = DownloadThread(url, ydl_opts)
        thread.progress_signal.connect(task_widget.update_progress)
        thread.complete_signal.connect(
            lambda info, fmt=options.format: self._on_complete(url, info, fmt)
        )
        thread.error_signal.connect(task_widget.set_error)
        thread.error_signal.connect(lambda msg: self.cleanup(url))
        thread.cancelled_signal.connect(task_widget.set_cancelled)
        thread.cancelled_signal.connect(lambda: self.cleanup(url))
        task_widget.cancel_requested.connect(lambda: self.cancel(url))

        self.download_threads[url] = thread
        thread.start()
        self.active_count_changed.emit(len(self.download_threads))

    def _cancel_existing(self, url):
        thread = self.download_threads[url]
        if thread.isRunning():
            thread.cancel()
            thread.wait()
        old_widget = self.active_tasks.get(url)
        if old_widget:
            self.tasks_page.remove_task_widget(old_widget)
            del self.active_tasks[url]

    def _on_complete(self, url, info, format_option):
        task_widget = self.active_tasks.get(url)
        if task_widget:
            task_widget.set_title(info.get("title", "未知"))
            task_widget.set_finished()
        self.history_item_completed.emit(info, format_option)
        self.cleanup(url)

    def cancel(self, url):
        thread = self.download_threads.get(url)
        if thread:
            thread.cancel()

    def cleanup(self, url):
        self.download_threads.pop(url, None)
        self.active_count_changed.emit(len(self.download_threads))

    def close_all(self):
        for thread in self.download_threads.values():
            thread.cancel()
```

- [ ] **Step 2: 验证并提交**

```bash
python -m py_compile download_controller.py
git add download_controller.py && git commit -m "refactor: 新增 DownloadController 下载编排控制器"
```

---

### Task 9: 重写 `ui.py` 为装配层，删除死代码

**Files:**
- Rewrite: `ui.py`
- Delete: `custom_events.py`

- [ ] **Step 1: 整体重写 `ui.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QButtonGroup,
    QSizePolicy,
    QStackedWidget,
    QMessageBox,
    QDialog,
    QFileDialog,
    QProgressDialog,
    QCheckBox,
    QPushButton,
)
from PyQt6.QtCore import Qt

from config import Config
from download_manager import DownloadManager
from download_options import DownloadOptions
from download_thread import AnalyzeThread
from download_controller import DownloadController
from generate_subtitle_dialog import GenerateSubtitleDialog
from history_manager import HistoryManager
from pages.new_download_page import NewDownloadPage
from pages.tasks_page import TasksPage
from styles import Styles
from subtitle_merger import SubtitleMergeThread
from tabs.history_tab import HistoryTab
from tabs.settings_tab import SettingsTab
from translation_dialog import TranslationDialog
from utils import get_language_code
from whisper_thread import WhisperThread


class YoutubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history_manager = HistoryManager()
        Config.load_config()
        self.download_history = []
        self.load_history()
        self.subtitle_merge_thread = None
        self.translation_dialog = None
        self.whisper_thread = None
        self.initUI()

    def init_logger(self, log_dir):
        if not log_dir:
            log_dir = Config.get_log_dir()
        Config.ensure_dirs(log_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"app_{timestamp}.log")
        from my_logger import MyLogger

        self.logger = MyLogger.get_instance(log_file)
        self.logger.info(
            f"应用程序启动于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.logger.info(f"日志目录: {log_dir}")

    def initUI(self):
        self.setWindowTitle(Config.APP_WINDOW_TITLE)
        self.resize(1000, 700)
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setStyleSheet(Styles.DARK_THEME)

        central_widget = QWidget()
        central_widget.setObjectName("MainContent")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        logo_label = QLabel("   YT Downloader")
        logo_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #ffffff; padding-bottom: 20px; border-bottom: 1px solid #3e3e42;"
        )
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(10)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.nav_btns = {}
        nav_items = [
            ("new_download", "⬇  新建下载"),
            ("tasks", "⚡  当前任务"),
            ("history", "🕒  历史记录"),
            ("settings", "⚙  设置"),
        ]

        for id, text in nav_items:
            btn = QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setProperty("class", "SidebarBtn")
            btn.setStyleSheet("")
            sidebar_layout.addWidget(btn)
            self.nav_group.addButton(btn)
            self.nav_btns[id] = btn
            btn.clicked.connect(lambda checked, page_id=id: self.switch_page(page_id))

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(30, 20, 30, 20)
        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages)
        main_layout.addWidget(content_area)

        self.init_pages()

        self.nav_btns["new_download"].click()

        log_dir = os.path.join(Config.DEFAULT_DOWNLOAD_PATH, "logs")
        self.init_logger(log_dir)

    def init_pages(self):
        self.new_download_page = NewDownloadPage()
        self.pages.addWidget(self.new_download_page)

        self.tasks_page = TasksPage()
        self.pages.addWidget(self.tasks_page)

        self.history_tab = HistoryTab()
        self.history_tab.request_clear_history.connect(self.clear_history)
        self.history_tab.request_export_history.connect(self.export_history)
        self.history_tab.set_history_data(self.download_history)
        self.history_tab.request_merge_subtitle.connect(self.merge_subtitle)
        self.history_tab.request_translate_subtitle.connect(self.translate_subtitle)
        self.history_tab.request_generate_subtitle.connect(self.generate_subtitle)
        self.pages.addWidget(self.history_tab)

        self.settings_tab = SettingsTab()
        self.pages.addWidget(self.settings_tab)

        self.controller = DownloadController(self.tasks_page, self)
        self.controller.active_count_changed.connect(self.update_active_tasks_count)
        self.controller.history_item_completed.connect(self.on_history_item_completed)

        self.new_download_page.analyze_requested.connect(self.analyze_url)
        self.new_download_page.download_requested.connect(self.start_download)

    def switch_page(self, page_id):
        index_map = {"new_download": 0, "tasks": 1, "history": 2, "settings": 3}
        if page_id in index_map:
            self.pages.setCurrentIndex(index_map[page_id])

    def update_active_tasks_count(self, count):
        if count > 0:
            self.nav_btns["tasks"].setText(f"⚡  当前任务 ({count})")
        else:
            self.nav_btns["tasks"].setText("⚡  当前任务")

    # ---- 分析 ----

    def analyze_url(self, url):
        self.analyze_thread = AnalyzeThread(self, url, {})
        self.analyze_thread.info_ready_signal.connect(
            self.new_download_page.show_video_info
        )
        self.analyze_thread.error_signal.connect(self.new_download_page.show_analyze_error)
        self.analyze_thread.finished.connect(self.new_download_page.reset_analyze_btn)
        self.analyze_thread.start()

    # ---- 下载 ----

    def start_download(self, url, format_option, download_path):
        if self.controller.has_active(url):
            reply = QMessageBox.question(
                self,
                "提示",
                "该任务已在下载列表中，是否重新下载？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建下载目录: {str(e)}")
                return

        settings = self.settings_tab.get_settings()
        options = self._build_download_options(url, format_option, download_path, settings)
        if options is None:
            return
        self.controller.start(options)

    def _build_download_options(self, url, format_option, download_path, settings):
        subtitle_options = None
        if settings.subtitle_enabled:
            subtitle_options = {"enabled": True}
            if settings.subtitle_language != "自动":
                code = get_language_code(settings.subtitle_language)
                if code:
                    subtitle_options["language"] = code

        speed_limit = settings.limit_rate if settings.limit_speed else None
        proxy = settings.proxy_url if settings.proxy_enabled else None

        if format_option == "仅字幕":
            selected = self.show_subtitle_options_dialog(settings)
            if not selected:
                return None
            subtitle_options = {"languages": selected}

        return DownloadOptions(
            url=url,
            format=format_option,
            download_path=download_path,
            subtitle=subtitle_options,
            proxy=proxy,
            speed_limit=speed_limit,
            use_chrome_cookies=settings.chrome_cookies,
        )

    def show_subtitle_options_dialog(self, settings):
        dialog = QDialog(self)
        dialog.setWindowTitle("选择字幕语言")
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet(Styles.DARK_THEME)

        layout = QVBoxLayout(dialog)
        lang_options = QHBoxLayout()

        zh_check = QCheckBox("中文")
        zh_check.setChecked("zh-Hans" in settings.only_langs)
        lang_options.addWidget(zh_check)

        en_check = QCheckBox("英文")
        en_check.setChecked("en" in settings.only_langs)
        lang_options.addWidget(en_check)

        jp_check = QCheckBox("日文")
        jp_check.setChecked("ja" in settings.only_langs)
        lang_options.addWidget(jp_check)

        layout.addLayout(lang_options)

        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        download_btn = QPushButton("下载")
        download_btn.clicked.connect(dialog.accept)
        download_btn.setProperty("class", "PrimaryBtn")
        download_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(download_btn)
        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_langs = []
            if zh_check.isChecked():
                selected_langs.append("zh-Hans")
            if en_check.isChecked():
                selected_langs.append("en")
            if jp_check.isChecked():
                selected_langs.append("ja")
            return selected_langs
        return None

    def on_history_item_completed(self, info, format_option):
        history_item = DownloadManager.get_download_info_from_result(info, format_option)
        history_item["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.download_history.append(history_item)
        self.save_history()
        self.history_tab.set_history_data(self.download_history)

    def load_history(self):
        self.download_history = self.history_manager.load_history()

    def save_history(self):
        self.history_manager.save_history(self.download_history)

    def closeEvent(self, event):
        self.save_history()
        self.controller.close_all()
        event.accept()

    # ---- 字幕功能 ----

    def merge_subtitle(self, video_path, subtitle_path):
        self.progress_dialog = QProgressDialog("正在合成字幕...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setWindowTitle("字幕合成")

        self.subtitle_merge_thread = SubtitleMergeThread(video_path, subtitle_path)
        self.subtitle_merge_thread.progress_signal.connect(
            lambda msg: self.progress_dialog.setLabelText(msg)
        )
        self.subtitle_merge_thread.finished_signal.connect(self.on_merge_finished)
        self.progress_dialog.canceled.connect(self.subtitle_merge_thread.cancel)

        self.subtitle_merge_thread.start()

    def on_merge_finished(self, success, message):
        self.progress_dialog.close()
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        self.subtitle_merge_thread = None

    def translate_subtitle(self, subtitle_path):
        settings = self.settings_tab.get_settings()
        if not settings.ai_api_key:
            QMessageBox.warning(self, "配置错误", "请先在设置中配置 ModelScope API Key")
            return

        self.translation_dialog = TranslationDialog(
            self,
            settings.ai_api_key,
            settings.ai_base_url,
            settings.ai_model,
            subtitle_path,
            settings.ai_batch_size,
        )
        self.translation_dialog.show()

    def generate_subtitle(self, video_path):
        dialog = GenerateSubtitleDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_language = dialog.get_selected_language()

        self.progress_dialog = QProgressDialog("正在生成字幕...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setWindowTitle("生成字幕")

        self.whisper_thread = WhisperThread(video_path, selected_language)
        self.whisper_thread.progress_signal.connect(
            lambda msg, *args: self.progress_dialog.setLabelText(msg)
        )
        self.whisper_thread.finished_signal.connect(
            lambda success, msg: self.on_generate_subtitle_finished(success, msg)
        )
        self.progress_dialog.canceled.connect(self.whisper_thread.cancel)

        self.whisper_thread.start()

    def on_generate_subtitle_finished(self, success, message):
        self.progress_dialog.close()
        if success:
            QMessageBox.information(self, "成功", f"字幕已生成:\n{message}")
        else:
            QMessageBox.critical(self, "失败", message)
        self.whisper_thread = None

    def clear_history(self):
        self.download_history = []
        self.save_history()
        self.history_tab.set_history_data(self.download_history)

    def export_history(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出历史记录",
            os.path.expanduser("~/Downloads/youtube_history.csv"),
            "CSV文件 (*.csv)",
        )
        if file_path:
            if self.history_manager.export_history_to_csv(
                file_path, self.download_history
            ):
                QMessageBox.information(
                    self, "导出成功", f"历史记录已导出到: {file_path}"
                )
            else:
                QMessageBox.critical(self, "导出失败", "导出历史记录时出错")
```

- [ ] **Step 2: 删除 `custom_events.py`**

```bash
rm custom_events.py
```

- [ ] **Step 3: 验证并提交**

```bash
python -m py_compile ui.py download_controller.py pages/new_download_page.py pages/tasks_page.py download_thread.py download_options.py constants.py
git add -A ui.py download_controller.py pages/ download_thread.py download_options.py constants.py
git rm --quiet custom_events.py
git commit -m "refactor: ui.py 瘦身为装配层，删除 custom_events 死代码"
```

---

### Task 10: 重写 `api_server.py`，去除 QThread 与忙轮询

**Files:**
- Rewrite: `api_server.py`

- [ ] **Step 1: 整体重写 `api_server.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import Config
from download_manager import DownloadManager
from download_worker import DownloadWorker

app = FastAPI(title="YouTube Downloader API")


class DownloadRequest(BaseModel):
    url: str
    format: str = Config.DEFAULT_FORMAT
    output_dir: Optional[str] = None
    subtitle: bool = False
    proxy: Optional[str] = None
    speed_limit: Optional[str] = None


class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str
    file_path: Optional[str] = None


manager = DownloadManager.get_instance()


@app.post("/api/v1/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest):
    try:
        subtitle_options = {"enabled": True} if request.subtitle else None

        ydl_opts = DownloadManager.prepare_download_options(
            format_option=request.format,
            download_path=request.output_dir or Config.DEFAULT_DOWNLOAD_PATH,
            subtitle_options=subtitle_options,
            limit=request.speed_limit,
            proxy=request.proxy,
            url=request.url,
        )

        task_id = manager.create_task(request.url, ydl_opts)
        task = manager.get_task(task_id)

        asyncio.create_task(_run_download(task_id, request.url, ydl_opts))

        return DownloadResponse(
            task_id=task_id,
            status=task["status"],
            message=task["message"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/status/{task_id}", response_model=DownloadResponse)
async def get_status(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return DownloadResponse(
        task_id=task_id,
        status=task["status"],
        message=task["message"],
        file_path=task.get("file_path"),
    )


@app.delete("/api/v1/download/{task_id}")
async def cancel_download(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    worker = task.get("worker")
    if worker and task["status"] in ("downloading", "pending"):
        worker.cancel()
        manager.update_task_status(task_id, "cancelled", "下载已取消")

    return {"message": "下载已取消"}


async def _run_download(task_id: str, url: str, options: dict):
    """异步下载：worker 在 to_thread 线程池运行，回调驱动状态更新，无忙轮询。"""
    task = manager.get_task(task_id)
    if not task:
        return

    manager.update_task_status(task_id, "downloading", "正在下载")

    def on_progress(progress):
        if progress["status"] == "downloading":
            downloaded = progress.get("downloaded_bytes", 0)
            total = progress.get("total_bytes", 0) or progress.get(
                "total_bytes_estimate", 0
            )
            if total > 0:
                percent = int(downloaded * 100 / total)
                manager.update_task_status(
                    task_id, "downloading", f"下载进度: {percent}%", percent
                )

    def on_complete(info):
        manager.update_task_status(task_id, "completed", "下载完成")
        if info and info.get("requested_downloads"):
            download_info = info["requested_downloads"][0]
            file_path = download_info.get("filepath")
            if file_path:
                task["file_path"] = file_path

    def on_error(message):
        if message == "cancelled":
            manager.update_task_status(task_id, "cancelled", "下载已取消")
        else:
            manager.update_task_status(task_id, "error", f"下载失败: {message}")

    worker = DownloadWorker(
        url,
        options,
        on_progress=on_progress,
        on_complete=on_complete,
        on_error=on_error,
    )
    task["worker"] = worker

    await asyncio.to_thread(worker.run)


def start_api_server(host=Config.API_HOST, port=Config.API_PORT):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()
```

- [ ] **Step 2: 验证并提交**

```bash
python -m py_compile api_server.py download_worker.py
git add api_server.py && git commit -m "refactor: api_server 改用 DownloadWorker，移除 QThread 忙轮询"
```

---

### Task 11: 全量验证

**Files:**
- 无代码改动，仅验证

- [ ] **Step 1: 全量语法编译检查**

```bash
python -m py_compile main.py ui.py api_server.py config.py constants.py download_manager.py download_options.py download_worker.py download_thread.py download_controller.py subtitle_merger.py ai_translator.py whisper_service.py whisper_thread.py history_manager.py utils.py styles.py my_logger.py task_widget.py translation_dialog.py generate_subtitle_dialog.py tabs/history_tab.py tabs/settings_tab.py pages/__init__.py pages/new_download_page.py pages/tasks_page.py
```

Expected: 无输出，退出码 0。

- [ ] **Step 2: 无 import 残留检查**

```bash
grep -rn "custom_events" --include="*.py" . || echo "OK: 无 custom_events 引用"
```

Expected: 打印 `OK: 无 custom_events 引用`。

- [ ] **Step 3: API 冒烟测试**

开一个终端跑 `python api_server.py`，然后：

```bash
curl -s -X POST http://127.0.0.1:8765/api/v1/download -H "Content-Type: application/json" -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "仅音频 (MP3)"}'
```

Expected: 返回含 `task_id` 与 `status` 的 JSON。然后：

```bash
curl -s http://127.0.0.1:8765/api/v1/status/<上一步返回的 task_id>
```

Expected: `status` 最终为 `completed`（下载完成后），且 **不再出现** `while thread.isRunning()` 忙轮询路径。

- [ ] **Step 4: GUI 冒烟测试**

```bash
python main.py
```

手动验证：窗口正常打开 → 输入链接点「分析链接」显示视频信息 → 选「最佳质量」点「开始下载」出现任务卡片并推进 → 点「取消」可取消 → 历史记录页出现该条记录 → 关闭窗口。

- [ ] **Step 5: 最终提交（如有遗漏修改）**

```bash
git status --short
git add -A && git commit -m "refactor: 冒烟验证通过" || echo "无变更"
```

---

## 计划自查记录

- **Spec 覆盖**：第 1 节拆分 ui.py → Task 7/8/9；第 2 节线程统一 → Task 3/4/10 + Task 9 删 custom_events；第 3 节常量与清理 → Task 1/5/6；第 4 节设置模型 → Task 2/6。不变量（API 路由、插件契约、历史格式）在 Task 10/1 未触碰。✓
- **占位符扫描**：每个步骤均含完整代码或精确命令，无 TBD/TODO。✓
- **类型一致性**：`DownloadOptions` 字段（url/format/download_path/subtitle/proxy/speed_limit/use_chrome_cookies）在 Task 2 定义、Task 8 消费、Task 9 组装，签名一致；`controller.active_count_changed(int)`、`history_item_completed(dict, str)` 与 Task 9 连接一致。✓
