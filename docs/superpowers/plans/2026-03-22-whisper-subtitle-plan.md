# Whisper 本地字幕生成功能 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 YouTube Downloader 添加本地 Whisper 语音转字幕功能，用户可通过右键菜单对已下载视频生成 .srt 字幕文件。

**Architecture:** 使用 openai-whisper 本地模型转写视频音频，通过 ffmpeg 提取音频，QThread 后台处理避免 UI 阻塞，语言选择对话框让用户指定或自动检测语言。

**Tech Stack:** Python, PyQt6, openai-whisper, ffmpeg

---

## 文件结构

```
video-downloader/
├── whisper_service.py          # 新增: Whisper 封装
├── whisper_thread.py          # 新增: QThread 后台线程
├── generate_subtitle_dialog.py # 新增: 语言选择对话框
├── tabs/
│   └── history_tab.py         # 修改: 右键菜单添加"生成字幕"
├── ui.py                       # 修改: 信号连接、进度对话框
└── requirements.txt           # 修改: 添加 whisper 依赖
```

---

## Task 1: whisper_service.py

**Files:**
- Create: `video-downloader/whisper_service.py`

- [ ] **Step 1: 编写 whisper_service.py**

```python
import whisper
import os


class WhisperService:
    def __init__(self):
        self.model = None

    def load_model(self, model_name="base"):
        """加载 Whisper 模型"""
        self.model = whisper.load_model(model_name)
        return self.model is not None

    def transcribe(self, audio_path, language=None):
        """
        执行语音转写
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码（None 表示自动检测）
            
        Returns:
            dict: Whisper 返回结果，包含 text, segments 等
        """
        if not self.model:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        options = {}
        if language:
            options["language"] = language

        result = self.model.transcribe(audio_path, **options)
        return result

    @staticmethod
    def to_srt(result):
        """
        将 Whisper 结果转换为 SRT 格式
        
        Args:
            result: Whisper transcribe 返回的结果
            
        Returns:
            str: SRT 格式字符串
        """
        segments = result.get("segments", [])
        srt_lines = []

        for i, segment in enumerate(segments, start=1):
            start = WhisperService._format_timestamp(segment["start"])
            end = WhisperService._format_timestamp(segment["end"])
            text = segment["text"].strip()

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")

        return "\n".join(srt_lines)

    @staticmethod
    def _format_timestamp(seconds):
        """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def extract_audio(video_path, output_path=None):
        """
        使用 ffmpeg 从视频提取音频
        
        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径（None 则生成临时文件）
            
        Returns:
            str: 音频文件路径
        """
        import subprocess

        if output_path is None:
            import tempfile
            output_path = os.path.join(tempfile.gettempdir(), "whisper_audio_temp.mp3")

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # 禁用视频
            "-acodec", "mp3",
            "-y",  # 覆盖已存在的文件
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_path
```

- [ ] **Step 2: 提交**

```bash
git add whisper_service.py
git commit -m "feat: add whisper_service.py for speech-to-text"
```

---

## Task 2: whisper_thread.py

**Files:**
- Create: `video-downloader/whisper_thread.py`

- [ ] **Step 1: 编写 whisper_thread.py**

```python
import os
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal


class WhisperThread(QThread):
    progress_signal = pyqtSignal(str, int, int)  # 状态消息, 当前步骤, 总步骤
    finished_signal = pyqtSignal(bool, str)  # 成功/失败, 文件路径或错误信息

    def __init__(self, video_path, language=None, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.language = language  # None 表示自动检测
        self.temp_audio_path = None

    def run(self):
        try:
            # 检查视频文件
            if not os.path.exists(self.video_path):
                raise FileNotFoundError(f"Video file not found: {self.video_path}")

            # 检查 ffmpeg
            import subprocess
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise RuntimeError("FFmpeg not found. Please install ffmpeg: brew install ffmpeg")

            self.progress_signal.emit("正在加载 Whisper 模型...", 1, 4)

            # 导入服务（延迟导入避免启动慢）
            from whisper_service import WhisperService

            service = WhisperService()
            if not service.load_model("base"):
                raise RuntimeError("Failed to load Whisper model")

            # 检查取消
            if self.isInterruptionRequested():
                self.finished_signal.emit(False, "已取消")
                return

            self.progress_signal.emit("正在提取音频...", 2, 4)

            # 提取音频
            self.temp_audio_path = service.extract_audio(self.video_path)

            # 检查取消
            if self.isInterruptionRequested():
                self._cleanup()
                self.finished_signal.emit(False, "已取消")
                return

            self.progress_signal.emit("正在转写中...", 3, 4)

            # 转写（此步骤为阻塞调用，优雅取消需等待完成）
            result = service.transcribe(self.temp_audio_path, language=self.language)

            # 检查取消（转写完成后检查）
            if self.isInterruptionRequested():
                self._cleanup()
                self.finished_signal.emit(False, "已取消")
                return

            # 生成 SRT
            srt_content = service.to_srt(result)

            # 保存文件
            video_dir = os.path.dirname(self.video_path)
            video_name = os.path.splitext(os.path.basename(self.video_path))[0]
            srt_path = os.path.join(video_dir, f"{video_name}.srt")

            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            self.progress_signal.emit("完成!", 4, 4)
            self.finished_signal.emit(True, srt_path)

        except Exception as e:
            self.finished_signal.emit(False, str(e))

        finally:
            # 清理临时文件
            self._cleanup()

    def _cleanup(self):
        if self.temp_audio_path and os.path.exists(self.temp_audio_path):
            try:
                os.remove(self.temp_audio_path)
            except:
                pass
            self.temp_audio_path = None

    def cancel(self):
        self.requestInterruption()
```

- [ ] **Step 2: 提交**

```bash
git add whisper_thread.py
git commit -m "feat: add WhisperThread for background transcription"
```

---

## Task 3: generate_subtitle_dialog.py

**Files:**
- Create: `video-downloader/generate_subtitle_dialog.py`

- [ ] **Step 1: 编写 generate_subtitle_dialog.py**

```python
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton)
from PyQt6.QtCore import Qt


class GenerateSubtitleDialog(QDialog):
    LANGUAGES = [
        ("自动检测", None),
        ("中文", "zh"),
        ("英文", "en"),
        ("日文", "ja"),
        ("韩文", "ko"),
        ("德文", "de"),
        ("法文", "fr"),
        ("西班牙文", "es"),
        ("葡萄牙文", "pt"),
        ("俄文", "ru"),
        ("意大利文", "it"),
        ("荷兰文", "nl"),
        ("波兰文", "pl"),
        ("土耳其文", "tr"),
        ("越南文", "vi"),
        ("泰文", "th"),
        ("阿拉伯文", "ar"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_language = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("生成字幕")
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px;
            }
            QPushButton {
                background-color: #3e3e42;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4e4e52;
            }
            QPushButton[class="primary"] {
                background-color: #0078d4;
            }
            QPushButton[class="primary"]:hover {
                background-color: #1084d8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 语言选择
        lang_layout = QHBoxLayout()
        lang_label = QLabel("选择语言:")
        lang_label.setMinimumWidth(80)
        self.lang_combo = QComboBox()

        for name, code in self.LANGUAGES:
            self.lang_combo.addItem(name, code)

        # 默认选择"自动检测"
        self.lang_combo.setCurrentIndex(0)

        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认")
        confirm_btn.setProperty("class", "primary")
        confirm_btn.clicked.connect(self.on_confirm)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def on_confirm(self):
        self.selected_language = self.lang_combo.currentData()
        self.accept()

    def get_selected_language(self):
        return self.selected_language
```

- [ ] **Step 2: 提交**

```bash
git add generate_subtitle_dialog.py
git commit -m "feat: add GenerateSubtitleDialog for language selection"
```

---

## Task 4: 修改 history_tab.py

**Files:**
- Modify: `video-downloader/tabs/history_tab.py`

- [ ] **Step 1: 添加信号定义 (约第15行附近)**

在 `request_translate_subtitle` 信号下方添加:

```python
request_generate_subtitle = pyqtSignal(str)  # video_path
```

- [ ] **Step 2: 右键菜单添加"生成字幕"选项 (约第122-128行)**

在 `translate_action` 之后添加:

```python
menu.addSeparator()

generate_action = QAction("生成字幕...", self)
generate_action.triggered.connect(lambda: self.prepare_generate_subtitle(history_item))
menu.addAction(generate_action)
```

- [ ] **Step 3: 添加 prepare_generate_subtitle 方法 (约第197行后)**

```python
def prepare_generate_subtitle(self, item):
    """准备生成字幕"""
    video_path = item.get('filepath')
    if not video_path:
        QMessageBox.warning(self, "错误", "找不到视频文件路径")
        return

    # 检查是否为字幕文件本身
    if video_path.endswith(('.srt', '.vtt')):
        QMessageBox.warning(self, "错误", "请选择一个视频文件，而非字幕文件")
        return

    if not os.path.exists(video_path):
        QMessageBox.warning(self, "错误", "视频文件不存在，可能已被移动或删除")
        return

    self.request_generate_subtitle.emit(video_path)
```

- [ ] **Step 4: 提交**

```bash
git add tabs/history_tab.py
git commit -m "feat: add generate subtitle option in context menu"
```

---

## Task 5: 修改 ui.py

**Files:**
- Modify: `video-downloader/ui.py`

- [ ] **Step 1: 添加导入 (约第28行)**

```python
from generate_subtitle_dialog import GenerateSubtitleDialog
from whisper_thread import WhisperThread
```

- [ ] **Step 2: 初始化时添加 thread 引用 (约第36行后)**

```python
self.whisper_thread = None
```

- [ ] **Step 3: 连接信号 (约第297行后，history_tab 信号连接处)**

在 `self.history_tab.request_translate_subtitle.connect(...)` 后添加:

```python
self.history_tab.request_generate_subtitle.connect(self.generate_subtitle)
```

- [ ] **Step 4: 添加 generate_subtitle 方法 (约第384行后，translate_subtitle 方法后)**

```python
def generate_subtitle(self, video_path):
    """处理生成字幕请求"""
    dialog = GenerateSubtitleDialog(self)
    if dialog.exec() != QDialog.Accepted:
        return

    selected_language = dialog.get_selected_language()

    # 创建进度对话框
    self.progress_dialog = QProgressDialog("正在生成字幕...", "取消", 0, 0, self)
    self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
    self.progress_dialog.setMinimumDuration(0)
    self.progress_dialog.setWindowTitle("生成字幕")

    # 创建线程
    self.whisper_thread = WhisperThread(video_path, selected_language)
    # progress_signal(str, int, int) - 使用 lambda 只取第一个参数（状态消息）
    self.whisper_thread.progress_signal.connect(lambda msg, *args: self.progress_dialog.setLabelText(msg))
    self.whisper_thread.finished_signal.connect(lambda success, msg: self.on_generate_subtitle_finished(success, msg))
    self.progress_dialog.canceled.connect(self.whisper_thread.cancel)

    self.whisper_thread.start()

def on_generate_subtitle_finished(self, success, message):
    """字幕生成完成回调"""
    self.progress_dialog.close()
    if success:
        QMessageBox.information(self, "成功", f"字幕已生成:\n{message}")
    else:
        QMessageBox.critical(self, "失败", message)

    self.whisper_thread = None
    self.progress_dialog.setMinimumDuration(0)
    self.progress_dialog.setWindowTitle("生成字幕")

    # 创建线程
    self.whisper_thread = WhisperThread(video_path, selected_language)
    # progress_signal(str, int, int) - 使用 lambda 只取第一个参数（状态消息）
    self.whisper_thread.progress_signal.connect(lambda msg, *args: self.progress_dialog.setLabelText(msg))
    self.whisper_thread.finished_signal.connect(lambda success, msg: self.on_generate_subtitle_finished(success, msg))
    self.progress_dialog.canceled.connect(self.whisper_thread.cancel)

    self.whisper_thread.start()

def on_generate_subtitle_finished(self, success, message):
    """字幕生成完成回调"""
    self.progress_dialog.close()
    if success:
        QMessageBox.information(self, "成功", f"字幕已生成:\n{message}")
    else:
        QMessageBox.critical(self, "失败", message)

    self.whisper_thread = None
```

- [ ] **Step 5: 提交**

```bash
git add ui.py
git commit -m "feat: connect whisper subtitle generation in UI"
```

---

## Task 6: 更新 requirements.txt

**Files:**
- Modify: `video-downloader/requirements.txt`

- [ ] **Step 1: 添加 whisper 依赖**

添加一行:

```
openai-whisper>=20231117
```

- [ ] **Step 2: 提交**

```bash
git add requirements.txt
git commit -m "chore: add openai-whisper dependency"
```

---

## Task 7: 完整测试

**Files:**
- 无文件变更

- [ ] **Step 1: 确保 ffmpeg 已安装**

```bash
ffmpeg -version
```
如果未安装: `brew install ffmpeg`

- [ ] **Step 2: 安装 whisper 依赖**

```bash
pip install openai-whisper
```

- [ ] **Step 3: 运行程序**

```bash
python main.py
```

- [ ] **Step 4: 测试流程**

1. 下载一个 YouTube 视频
2. 打开历史记录，右键点击该视频
3. 选择"生成字幕..."
4. 在对话框中选择语言（默认"自动检测"），点击确认
5. 观察进度对话框，等待生成完成
6. 检查视频同目录下是否生成了 .srt 文件

- [ ] **Step 5: 测试错误处理 - 文件不存在**

1. 在历史记录中右键点击视频
2. 选择"生成字幕..."
3. 临时移动视频文件到其他位置
4. 点击确认，观察是否提示"视频文件不存在"

- [ ] **Step 6: 测试错误处理 - FFmpeg 未安装**

1. 临时重命名 ffmpeg: `mv /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg.bak`
2. 重复生成字幕流程
3. 应提示 "FFmpeg not found..."
4. 恢复: `mv /usr/local/bin/ffmpeg.bak /usr/local/bin/ffmpeg`

- [ ] **Step 7: 测试取消功能**

1. 选择生成字幕
2. 在进度对话框显示时点击"取消"
3. 确认临时音频文件被清理

---

## 总结

| Task | 文件 | 状态 |
|------|------|------|
| 1 | whisper_service.py | ⬜ |
| 2 | whisper_thread.py | ⬜ |
| 3 | generate_subtitle_dialog.py | ⬜ |
| 4 | history_tab.py | ⬜ |
| 5 | ui.py | ⬜ |
| 6 | requirements.txt | ⬜ |
| 7 | 测试 | ⬜ |

---

## 附录: 安装指引

### FFmpeg (macOS)
```bash
brew install ffmpeg
```

### Whisper
```bash
pip install openai-whisper
```

首次运行 Whisper 会自动下载 base 模型（约 74MB）。
