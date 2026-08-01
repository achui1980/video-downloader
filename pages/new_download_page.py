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
