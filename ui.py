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

        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        history_title = QLabel("历史记录")
        history_title.setObjectName("PageTitle")
        history_layout.addWidget(history_title)

        self.history_tab = HistoryTab()
        self.history_tab.request_clear_history.connect(self.clear_history)
        self.history_tab.request_export_history.connect(self.export_history)
        self.history_tab.set_history_data(self.download_history)
        self.history_tab.request_merge_subtitle.connect(self.merge_subtitle)
        self.history_tab.request_translate_subtitle.connect(self.translate_subtitle)
        self.history_tab.request_generate_subtitle.connect(self.generate_subtitle)
        history_layout.addWidget(self.history_tab)
        self.pages.addWidget(history_page)

        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_title = QLabel("设置")
        settings_title.setObjectName("PageTitle")
        settings_layout.addWidget(settings_title)

        self.settings_tab = SettingsTab()
        settings_layout.addWidget(self.settings_tab)
        self.pages.addWidget(settings_page)

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
