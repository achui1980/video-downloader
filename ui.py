#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QStackedWidget,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QFormLayout,
    QApplication,
    QScrollArea,
    QFrame,
    QToolButton,
    QButtonGroup,
    QSizePolicy,
    QGridLayout,
    QProgressDialog,
)
from PyQt6.QtCore import Qt, QSize, QMetaObject, QThread
from PyQt6.QtGui import QIcon, QFont, QAction
import yt_dlp
from download_manager import DownloadManager
from download_thread import DownloadThread, AnalyzeThread
from subtitle_merger import SubtitleMergeThread
from custom_events import (
    ShowMessageEvent,
    UpdateStatusEvent,
    UpdateVideoInfoEvent,
    handle_custom_event,
)
from utils import format_duration, format_size, format_time, get_language_code
from history_manager import HistoryManager
from tabs.history_tab import HistoryTab
from tabs.settings_tab import SettingsTab
from styles import Styles
from task_widget import TaskWidget
from config import Config
from translation_dialog import TranslationDialog
from generate_subtitle_dialog import GenerateSubtitleDialog
from whisper_thread import WhisperThread


class YoutubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_threads = {}
        self.download_history = []
        self.active_tasks = {}  # Map url to TaskWidget
        self.subtitle_merge_thread = None
        self.translation_dialog = None
        self.whisper_thread = None

        # 初始化历史记录管理器
        self.history_manager = HistoryManager()
        # 加载配置
        Config.load_config()
        # 加载历史记录
        self.load_history()
        self.initUI()
        # 修复自定义事件处理方法的绑定
        # 使用 lambda 函数来正确传递参数
        self.customEvent = lambda event: handle_custom_event(self, event)

    def init_logger(self, log_dir):
        """初始化日志系统"""
        # 获取应用程序启动目录
        if not log_dir:
            log_dir = Config.get_log_dir()

        # 确保日志目录存在
        Config.ensure_dirs(log_dir)

        # 创建应用程序日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"app_{timestamp}.log")

        # 初始化日志记录器
        from my_logger import MyLogger

        self.logger = MyLogger.get_instance(log_file)

        # 记录应用程序启动信息
        self.logger.info(
            f"应用程序启动于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.logger.info(f"日志目录: {log_dir}")

    def initUI(self):
        self.setWindowTitle(Config.APP_WINDOW_TITLE)
        self.resize(1000, 700)  # 调整默认尺寸以适应新布局
        self.setWindowState(Qt.WindowState.WindowMaximized)  # 启动时最大化
        self.setStyleSheet(Styles.DARK_THEME)

        # 主窗口部件
        central_widget = QWidget()
        central_widget.setObjectName("MainContent")
        self.setCentralWidget(central_widget)

        # 全局布局：左侧侧边栏 + 右侧内容区
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 左侧侧边栏 ---
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        # Logo 区域
        logo_label = QLabel("   YT Downloader")
        logo_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #ffffff; padding-bottom: 20px; border-bottom: 1px solid #3e3e42;"
        )
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(10)

        # 导航按钮组
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
            btn.setProperty("class", "SidebarBtn")  # 用于 QSS
            # 强制应用类名，因为 PyQt 有时不会自动更新动态属性的样式
            btn.setStyleSheet("")

            sidebar_layout.addWidget(btn)
            self.nav_group.addButton(btn)
            self.nav_btns[id] = btn

            # 连接点击事件
            btn.clicked.connect(lambda checked, page_id=id: self.switch_page(page_id))

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # --- 右侧内容区 ---
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(30, 20, 30, 20)

        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages)

        main_layout.addWidget(content_area)

        # --- 初始化各个页面 ---
        self.init_new_download_page()
        self.init_tasks_page()
        self.init_history_page()
        self.init_settings_page()

        # 默认选中第一个页面
        self.nav_btns["new_download"].click()

        # 初始化日志系统
        log_dir = os.path.join(Config.DEFAULT_DOWNLOAD_PATH, "logs")
        self.init_logger(log_dir)

    def init_new_download_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(20)

        # 页面标题
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
        self.analyze_btn.clicked.connect(self.analyze_url)
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

        # 格式
        grid.addWidget(QLabel("下载格式"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(
            [
                Config.DEFAULT_FORMAT,
                "仅视频",
                "仅音频 (MP3)",
                "仅字幕",
                "1080p",
                "720p",
                "480p",
                "360p",
            ]
        )
        grid.addWidget(self.format_combo, 0, 1)

        # 保存位置
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

        # 系统
        grid.addWidget(QLabel("系统平台"), 1, 0)
        self.system_combo = QComboBox()
        self.system_combo.addItems([Config.DEFAULT_SYSTEM, "Windows", "Linux"])
        self.system_combo.setCurrentText(Config.DEFAULT_SYSTEM)
        grid.addWidget(self.system_combo, 1, 1)

        config_layout.addLayout(grid)

        # 底部操作栏
        action_row = QHBoxLayout()
        action_row.addStretch()

        self.download_btn = QPushButton("开始下载")
        self.download_btn.setProperty("class", "PrimaryBtn")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self.start_download)
        action_row.addWidget(self.download_btn)

        config_layout.addLayout(action_row)
        layout.addWidget(config_card)

        # 视频信息预览区 (初始隐藏)
        self.video_info_card = QFrame()
        self.video_info_card.setProperty("class", "Card")
        self.video_info_card.setVisible(False)
        info_layout = QVBoxLayout(self.video_info_card)
        self.video_info_label = QLabel()
        info_layout.addWidget(self.video_info_label)
        layout.addWidget(self.video_info_card)

        layout.addStretch()
        self.pages.addWidget(page)

    def init_tasks_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("当前任务")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # 任务列表区域 (滚动区域)
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

        self.pages.addWidget(page)

    def init_history_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("历史记录")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.history_tab = HistoryTab()
        self.history_tab.request_clear_history.connect(self.clear_history)
        self.history_tab.request_export_history.connect(self.export_history)
        self.history_tab.set_history_data(self.download_history)
        # 连接字幕合成信号
        self.history_tab.request_merge_subtitle.connect(self.merge_subtitle)
        # 连接字幕翻译信号
        self.history_tab.request_translate_subtitle.connect(self.translate_subtitle)
        self.history_tab.request_generate_subtitle.connect(self.generate_subtitle)

        layout.addWidget(self.history_tab)
        self.pages.addWidget(page)

    def init_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("设置")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.settings_tab = SettingsTab()
        layout.addWidget(self.settings_tab)

        self.pages.addWidget(page)

    def switch_page(self, page_id):
        # 简单的映射：new_download->0, tasks->1, history->2, settings->3
        index_map = {"new_download": 0, "tasks": 1, "history": 2, "settings": 3}
        if page_id in index_map:
            self.pages.setCurrentIndex(index_map[page_id])

    def update_active_tasks_count(self):
        """更新当前任务按钮上的计数显示"""
        count = len(self.download_threads)
        if count > 0:
            self.nav_btns["tasks"].setText(f"⚡  当前任务 ({count})")
        else:
            self.nav_btns["tasks"].setText("⚡  当前任务")

    def cleanup_thread(self, url):
        """清理已结束的下载线程并更新计数"""
        if url in self.download_threads:
            del self.download_threads[url]
        self.update_active_tasks_count()

    def merge_subtitle(self, video_path, subtitle_path):
        """处理字幕合成请求"""
        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在合成字幕...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setWindowTitle("字幕合成")

        # 创建线程
        self.subtitle_merge_thread = SubtitleMergeThread(video_path, subtitle_path)
        self.subtitle_merge_thread.progress_signal.connect(
            lambda msg: self.progress_dialog.setLabelText(msg)
        )
        self.subtitle_merge_thread.finished_signal.connect(self.on_merge_finished)
        self.progress_dialog.canceled.connect(self.subtitle_merge_thread.cancel)

        self.subtitle_merge_thread.start()

    def on_merge_finished(self, success, message):
        """字幕合成完成回调"""
        self.progress_dialog.close()
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)

        self.subtitle_merge_thread = None

    def translate_subtitle(self, subtitle_path):
        """处理字幕翻译请求"""
        api_key = self.settings_tab.ai_api_key.text().strip()
        base_url = self.settings_tab.ai_base_url.text().strip()
        model = self.settings_tab.ai_model.text().strip()

        batch_size = 200
        try:
            batch_size = int(self.settings_tab.ai_batch_size.text().strip())
        except ValueError:
            batch_size = 200

        if not api_key:
            QMessageBox.warning(self, "配置错误", "请先在设置中配置 ModelScope API Key")
            return

        self.translation_dialog = TranslationDialog(
            self, api_key, base_url, model, subtitle_path, batch_size
        )
        self.translation_dialog.show()

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
        self.whisper_thread.progress_signal.connect(
            lambda msg, *args: self.progress_dialog.setLabelText(msg)
        )
        self.whisper_thread.finished_signal.connect(
            lambda success, msg: self.on_generate_subtitle_finished(success, msg)
        )
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

    # --- 以下是业务逻辑方法，保持原有逻辑不变 ---

    def paste_from_clipboard(self):
        """从剪切板粘贴内容到 URL 输入框"""
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

    def analyze_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return

        self.analyze_btn.setText("分析中...")
        self.analyze_btn.setEnabled(False)
        self.video_info_card.setVisible(True)
        self.video_info_label.setText("正在获取视频信息，请稍候...")

        # 准备分析选项
        ydl_opts = {}
        if (
            hasattr(self, "chrome_cookies_check")
            and self.chrome_cookies_check.isChecked()
        ):
            ydl_opts["cookiesfrombrowser"] = ("chrome",)

        self.analyze_thread = AnalyzeThread(self, url, ydl_opts)
        self.analyze_thread.info_ready_signal.connect(self.update_video_info)
        self.analyze_thread.error_signal.connect(
            lambda msg: self.video_info_label.setText(f"错误: {msg}")
        )
        self.analyze_thread.finished.connect(lambda: self.analyze_btn.setEnabled(True))
        self.analyze_thread.finished.connect(
            lambda: self.analyze_btn.setText("分析链接")
        )
        self.analyze_thread.start()

    def update_video_info(self, info):
        if not info:
            return

        info_text = f"<b>{info.get('title', '未知')}</b><br>"
        info_text += f"上传者: {info.get('uploader', '未知')} | "
        info_text += f"时长: {format_duration(info.get('duration', 0))} | "
        info_text += f"日期: {info.get('upload_date', '未知')}<br>"

        # 提取字幕信息
        subtitles = info.get("subtitles", {})
        auto_captions = info.get("automatic_captions", {})

        all_langs = set()
        if subtitles:
            all_langs.update(subtitles.keys())
        if auto_captions:
            all_langs.update(auto_captions.keys())

        if all_langs:
            # 整理语言列表，优先显示常用语言
            priority_langs = ["zh-Hans", "zh-Hant", "en", "ja", "ko"]
            display_langs = []

            for lang in priority_langs:
                if lang in all_langs:
                    display_langs.append(lang)
                    all_langs.remove(lang)

            # 添加剩余的语言（最多显示5个）
            sorted_remaining = sorted(list(all_langs))
            display_langs.extend(sorted_remaining[:5])

            langs_str = ", ".join(display_langs)
            if len(all_langs) > 5:
                langs_str += f" 等 {len(all_langs) + len(display_langs)} 种语言"

            info_text += f"支持字幕: {langs_str}"
        else:
            info_text += "支持字幕: 无"

        self.video_info_label.setText(info_text)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return

        # 检查是否重复
        if url in self.download_threads:
            reply = QMessageBox.question(
                self,
                "提示",
                "该任务已在下载列表中，是否重新下载？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return
            if self.download_threads[url].isRunning():
                self.download_threads[url].cancel()
                self.download_threads[url].wait()
            if url in self.active_tasks:
                old_widget = self.active_tasks[url]
                self.tasks_container_layout.removeWidget(old_widget)
                old_widget.deleteLater()
                del self.active_tasks[url]

        download_path = self.download_path.text()
        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建下载目录: {str(e)}")
                return

        # 准备选项 (保持原逻辑)
        subtitle_options = None
        if self.settings_tab.subtitle_check.isChecked():
            subtitle_options = {"enabled": True}
            if (
                hasattr(self.settings_tab, "subtitle_lang_combo")
                and self.settings_tab.subtitle_lang_combo.currentText() != "自动"
            ):
                selected_lang = self.settings_tab.subtitle_lang_combo.currentText()
                lang_code = get_language_code(selected_lang)
                if lang_code:
                    subtitle_options["language"] = lang_code

        limit = None
        if (
            self.settings_tab.limit_check.isChecked()
            and self.settings_tab.limit_input.text().strip()
        ):
            limit = self.settings_tab.limit_input.text().strip()

        proxy = None
        if (
            self.settings_tab.proxy_check.isChecked()
            and self.settings_tab.proxy_input.text().strip()
        ):
            proxy = self.settings_tab.proxy_input.text().strip()

        use_chrome_cookies = False
        if hasattr(self.settings_tab, "chrome_cookies_check"):
            use_chrome_cookies = self.settings_tab.chrome_cookies_check.isChecked()

        format_option = self.format_combo.currentText()
        if format_option == "仅字幕":
            selected_langs = self.show_subtitle_options_dialog()
            if not selected_langs:
                return
            else:
                subtitle_options = {"languages": selected_langs}

        ydl_opts = DownloadManager.prepare_download_options(
            format_option,
            download_path,
            subtitle_options,
            limit,
            proxy,
            use_chrome_cookies,
            enable_logging=True,
            url=url,
        )

        # 切换到任务页
        # self.nav_btns["tasks"].click() # 不再自动切换到任务页

        # 创建任务组件
        task_widget = TaskWidget(url, title=f"正在解析: {url}")
        self.tasks_container_layout.addWidget(task_widget)
        self.active_tasks[url] = task_widget

        download_thread = DownloadThread(url, ydl_opts)
        download_thread.progress_signal.connect(task_widget.update_progress)
        download_thread.complete_signal.connect(
            lambda info: self.download_complete(url, info)
        )

        # 错误和取消时，清理线程并更新计数
        download_thread.error_signal.connect(task_widget.set_error)
        download_thread.error_signal.connect(lambda msg: self.cleanup_thread(url))

        download_thread.cancelled_signal.connect(task_widget.set_cancelled)
        download_thread.cancelled_signal.connect(lambda: self.cleanup_thread(url))

        task_widget.cancel_requested.connect(lambda: self.cancel_download(url))

        self.download_threads[url] = download_thread
        download_thread.start()

        # 更新任务计数
        self.update_active_tasks_count()

    def load_history(self):
        self.download_history = self.history_manager.load_history()

    def save_history(self):
        self.history_manager.save_history(self.download_history)

    def download_complete(self, url, info):
        if url in self.active_tasks:
            task_widget = self.active_tasks[url]
            title = info.get("title", "未知")
            task_widget.set_title(title)
            task_widget.set_finished()

        format_option = self.format_combo.currentText()
        history_item = DownloadManager.get_download_info_from_result(
            info, format_option
        )
        history_item["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.download_history.append(history_item)
        self.save_history()
        self.history_tab.set_history_data(self.download_history)

        # 清理线程
        self.cleanup_thread(url)

    def closeEvent(self, event):
        self.save_history()
        event.accept()
        for url, thread in self.download_threads.items():
            thread.cancel()

    def cancel_download(self, url):
        if url in self.download_threads:
            self.download_threads[url].cancel()

    def show_subtitle_options_dialog(self):
        # 保持原有的字幕对话框逻辑，仅需确保样式适配
        from PyQt6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QHBoxLayout,
            QCheckBox,
            QPushButton,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("选择字幕语言")
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet(Styles.DARK_THEME)  # 应用深色主题

        layout = QVBoxLayout(dialog)
        lang_options = QHBoxLayout()

        zh_check = QCheckBox("中文")
        zh_check.setChecked(self.settings_tab.zh_subtitle_check.isChecked())
        lang_options.addWidget(zh_check)

        en_check = QCheckBox("英文")
        en_check.setChecked(self.settings_tab.en_subtitle_check.isChecked())
        lang_options.addWidget(en_check)

        jp_check = QCheckBox("日文")
        jp_check.setChecked(self.settings_tab.jp_subtitle_check.isChecked())
        lang_options.addWidget(jp_check)

        layout.addLayout(lang_options)

        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        download_btn = QPushButton("下载")
        download_btn.clicked.connect(dialog.accept)
        download_btn.setProperty("class", "PrimaryBtn")  # 使用主按钮样式
        download_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(download_btn)
        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 简化的逻辑：只返回选中的语言
            selected_langs = []
            if zh_check.isChecked():
                selected_langs.append("zh-Hans")
            if en_check.isChecked():
                selected_langs.append("en")
            if jp_check.isChecked():
                selected_langs.append("ja")
            return selected_langs
        return None

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
