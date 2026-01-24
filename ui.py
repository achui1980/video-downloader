#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import threading
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QProgressBar, QComboBox,
                             QCheckBox, QFileDialog, QMessageBox, QTabWidget, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout,
                             QApplication, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QSize, QMetaObject, QThread
from PyQt6.QtGui import QIcon, QFont
import yt_dlp
from download_manager import DownloadManager
from download_thread import DownloadThread, AnalyzeThread
from custom_events import ShowMessageEvent, UpdateStatusEvent, UpdateVideoInfoEvent, handle_custom_event
from utils import format_duration, format_size, format_time, get_language_code
from history_manager import HistoryManager
from tabs.history_tab import HistoryTab
from tabs.settings_tab import SettingsTab
from styles import Styles
from task_widget import TaskWidget
from config import Config

class YoutubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_threads = {}
        self.download_history = []
        self.active_tasks = {} # Map url to TaskWidget
        
        # 初始化历史记录管理器
        self.history_manager = HistoryManager()
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
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'app_{timestamp}.log')
        
        # 初始化日志记录器
        from my_logger import MyLogger
        self.logger = MyLogger.get_instance(log_file)
        
        # 记录应用程序启动信息
        self.logger.info(f"应用程序启动于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"日志目录: {log_dir}")
        
    def initUI(self):
        self.setWindowTitle(Config.APP_WINDOW_TITLE)
        self.setGeometry(100, 100, Config.APP_WINDOW_SIZE[0], Config.APP_WINDOW_SIZE[1])
        self.setStyleSheet(Styles.DARK_THEME)
        
        # 创建主窗口部件和布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- 顶部区域：输入与核心操作 ---
        top_section = QVBoxLayout()
        top_section.setSpacing(10)
        
        # URL 输入行
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("在此粘贴 YouTube 视频链接...")
        self.url_input.setMinimumHeight(40)
        self.url_input.setFont(QFont("Segoe UI", 12))
        url_layout.addWidget(self.url_input)
        
        self.analyze_btn = QPushButton("分析链接")
        self.analyze_btn.setMinimumHeight(40)
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self.analyze_url)
        url_layout.addWidget(self.analyze_btn)
        
        top_section.addLayout(url_layout)
        
        # --- 配置区域 (可折叠/分组) ---
        config_group = QGroupBox("下载配置")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)
        
        # 第一行配置：路径与格式
        row1_layout = QHBoxLayout()
        
        # 格式选择
        row1_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([Config.DEFAULT_FORMAT, "仅视频", "仅音频 (MP3)", "仅字幕", "1080p", "720p", "480p", "360p"])
        self.format_combo.setMinimumWidth(120)
        row1_layout.addWidget(self.format_combo)
        
        # 系统选择
        row1_layout.addWidget(QLabel("系统:"))
        self.system_combo = QComboBox()
        self.system_combo.addItems([Config.DEFAULT_SYSTEM, "Windows", "Linux"])
        self.system_combo.setCurrentText(Config.DEFAULT_SYSTEM)
        row1_layout.addWidget(self.system_combo)
        
        row1_layout.addStretch()
        
        # 保存路径
        row1_layout.addWidget(QLabel("保存至:"))
        self.download_path = QLineEdit()
        self.download_path.setText(Config.DEFAULT_DOWNLOAD_PATH)
        row1_layout.addWidget(self.download_path)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_folder)
        row1_layout.addWidget(self.browse_btn)
        
        config_layout.addLayout(row1_layout)
        
        top_section.addWidget(config_group)
        
        # 下载按钮 (醒目)
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setMinimumHeight(45)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0098ff; }
            QPushButton:pressed { background-color: #005c99; }
        """)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self.start_download)
        top_section.addWidget(self.download_btn)
        
        main_layout.addLayout(top_section)

         # 初始化日志系统
        log_dir = os.path.join(self.download_path.text(), 'logs')
        self.init_logger(log_dir)
        
        # --- 中部区域：Tab页 (任务列表/历史/设置) ---
        tabs = QTabWidget()
        
        # 1. 当前任务 Tab (替代原来的 "全部")
        tasks_tab = QWidget()
        tasks_layout = QVBoxLayout(tasks_tab)
        tasks_layout.setContentsMargins(0, 10, 0, 0)
        
        # 视频信息显示 (保留，用于分析结果)
        self.video_info = QTextEdit()
        self.video_info.setReadOnly(True)
        self.video_info.setMaximumHeight(80)
        self.video_info.setPlaceholderText("视频信息将显示在这里...")
        tasks_layout.addWidget(self.video_info)
        
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
        tasks_layout.addWidget(scroll_area)
        
        # 2. 历史记录 Tab
        self.history_tab = HistoryTab()
        self.history_tab.request_clear_history.connect(self.clear_history)
        self.history_tab.request_export_history.connect(self.export_history)
        self.history_tab.set_history_data(self.download_history)
        
        # 3. 设置 Tab
        self.settings_tab = SettingsTab()
        
        tabs.addTab(tasks_tab, "当前任务")
        tabs.addTab(self.history_tab, "历史记录")
        tabs.addTab(self.settings_tab, "设置")
        
        main_layout.addWidget(tabs)
        
        # 状态栏 (简化)
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #808080;")
        main_layout.addWidget(self.status_label)
        
        self.setCentralWidget(main_widget)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择下载文件夹", self.download_path.text())
        if folder:
            self.download_path.setText(folder)
    
    def analyze_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return
        
        self.status_label.setText("正在分析视频信息...")
        self.video_info.clear()
        self.video_info.setText("正在获取视频信息，请稍候...")
        
        # 准备分析选项
        ydl_opts = {}
        
        # 添加Chrome浏览器Cookies选项
        if hasattr(self, 'chrome_cookies_check') and self.chrome_cookies_check.isChecked():
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
        
        # 创建分析线程
        self.analyze_thread = AnalyzeThread(self, url, ydl_opts)
        
        # 连接信号到槽函数
        self.analyze_thread.info_ready_signal.connect(self.update_video_info)
        self.analyze_thread.error_signal.connect(lambda msg: self.video_info.setText(f"错误: {msg}"))
        self.analyze_thread.status_signal.connect(self.status_label.setText)
        
        # 启动线程
        self.analyze_thread.start()
    
    def update_video_info(self, info):
        if not info:
            return
            
        info_text = f"标题: {info.get('title', '未知')}\n"
        info_text += f"上传者: {info.get('uploader', '未知')}\n"
        info_text += f"时长: {format_duration(info.get('duration', 0))}\n"
        info_text += f"上传日期: {info.get('upload_date', '未知')}\n"
        
        # 添加字幕语言支持信息
        if 'subtitles' in info and info['subtitles']:
            available_subtitles = info['subtitles'].keys()
            count = len(available_subtitles)
            info_text += f"字幕: 支持 {count} 种语言\n"
        else:
            info_text += "字幕: 无\n"
        
        self.video_info.setText(info_text)
        self.status_label.setText("分析完成")
        
    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return
        
        # 允许重复下载，或者检查是否正在下载
        if url in self.download_threads:
            reply = QMessageBox.question(self, "提示", "该任务已在下载列表中，是否重新下载？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            # 如果是重新下载，先取消旧任务（如果还在运行）
            if self.download_threads[url].isRunning():
                self.download_threads[url].cancel()
                self.download_threads[url].wait()
            # 移除旧的UI组件
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
        
        # 准备字幕选项
        subtitle_options = None
        if self.settings_tab.subtitle_check.isChecked():
            subtitle_options = {
                'enabled': True
            }
            if hasattr(self.settings_tab, 'subtitle_lang_combo') and self.settings_tab.subtitle_lang_combo.currentText() != "自动":
                selected_lang = self.settings_tab.subtitle_lang_combo.currentText()
                lang_code = get_language_code(selected_lang)
                if lang_code:
                    subtitle_options['language'] = lang_code
        
        # 获取下载速度限制
        limit = None
        if self.settings_tab.limit_check.isChecked() and self.settings_tab.limit_input.text().strip():
            limit = self.settings_tab.limit_input.text().strip()
        
        # 获取代理设置
        proxy = None
        if self.settings_tab.proxy_check.isChecked() and self.settings_tab.proxy_input.text().strip():
            proxy = self.settings_tab.proxy_input.text().strip()
        
        # 获取Chrome浏览器cookies设置
        use_chrome_cookies = False
        if hasattr(self.settings_tab, 'chrome_cookies_check'):
            use_chrome_cookies = self.settings_tab.chrome_cookies_check.isChecked()
        
        # 使用DownloadManager来准备下载选项
        format_option = self.format_combo.currentText()
        if format_option == "仅字幕":
            selected_langs = self.show_subtitle_options_dialog()
            if not selected_langs:
                return  # 用户取消了操作
            else:
                subtitle_options = {
                    'languages': selected_langs
                }
        
        ydl_opts = DownloadManager.prepare_download_options(
            format_option, 
            download_path, 
            subtitle_options, 
            limit, 
            proxy, 
            use_chrome_cookies,
            enable_logging=True,
            url=url
        )
        
        # 创建 TaskWidget 并添加到 UI
        task_widget = TaskWidget(url, title=f"正在解析: {url}")
        self.tasks_container_layout.addWidget(task_widget)
        self.active_tasks[url] = task_widget
        
        # 创建下载线程
        download_thread = DownloadThread(url, ydl_opts)
        
        # 连接信号到 TaskWidget
        download_thread.progress_signal.connect(task_widget.update_progress)
        download_thread.complete_signal.connect(lambda info: self.download_complete(url, info))
        download_thread.error_signal.connect(task_widget.set_error)
        download_thread.cancelled_signal.connect(task_widget.set_cancelled)
        
        # 连接 TaskWidget 的取消信号到线程
        task_widget.cancel_requested.connect(lambda: self.cancel_download(url))
        
        # 保存线程引用
        self.download_threads[url] = download_thread
        
        self.status_label.setText(f"已开始下载: {url}")
        
        # 启动下载线程
        download_thread.start()
    
    def load_history(self):
        """加载历史记录"""
        self.download_history = self.history_manager.load_history()
    
    def save_history(self):
        """保存历史记录到文件"""
        self.history_manager.save_history(self.download_history)

    def populate_example_data(self):
        """填充示例数据到下载表格 - 已废弃，但保留以兼容旧代码"""
        # 这个方法之前用于填充 self.download_table
        # 现在历史记录由 self.history_tab 管理
        if hasattr(self, 'history_tab'):
            self.history_tab.set_history_data(self.download_history)
    
    def download_complete(self, url, info):
        # 更新 TaskWidget 状态
        if url in self.active_tasks:
            task_widget = self.active_tasks[url]
            # 获取标题更新UI
            title = info.get('title', '未知')
            task_widget.set_title(title)
            task_widget.set_finished()
            
            # 延迟移除或保留？现在保留在列表中让用户看到完成状态
            # self.tasks_container_layout.removeWidget(task_widget)
            # task_widget.deleteLater()
            # del self.active_tasks[url]

        format_option = self.format_combo.currentText()
        
        # 使用DownloadManager获取下载结果信息
        history_item = DownloadManager.get_download_info_from_result(info, format_option)
        
        # 添加时间戳
        history_item['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存到历史记录列表
        self.download_history.append(history_item)
        
        # 保存历史记录到文件
        self.save_history()
        
        # 更新历史记录表格数据源
        self.history_tab.set_history_data(self.download_history)
        
        self.status_label.setText("下载完成")
        
        # 清理线程引用
        if url in self.download_threads:
            del self.download_threads[url]
    
    def closeEvent(self, event):
        self.save_history()
        event.accept()
        
        # 停止所有正在进行的下载
        for url, thread in self.download_threads.items():
            thread.cancel()
    
    def cancel_download(self, url):
        if url in self.download_threads:
            self.status_label.setText("正在取消...")
            self.download_threads[url].cancel()
            # 线程清理会在 cancelled_signal 中处理，或者在这里做

    def show_subtitle_options_dialog(self):
        """显示字幕选项对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("选择字幕语言")
        dialog.setMinimumWidth(300)
        # 应用样式
        dialog.setStyleSheet(Styles.DARK_THEME)
        
        layout = QVBoxLayout(dialog)
        
        # 使用设置选项卡中的字幕选择
        lang_options = QHBoxLayout()
        
        # 复制设置选项卡中的字幕选择状态
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
        
        # 添加按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        download_btn = QPushButton("下载")
        download_btn.clicked.connect(dialog.accept)
        download_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(download_btn)
        layout.addLayout(button_layout)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 更新设置选项卡中的字幕选择状态
            # 创建对话框中复选框的映射，以便快速查找
            dialog_checkboxes = {}
            for i in range(lang_options.count()):
                widget = lang_options.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    dialog_checkboxes[widget.text()] = widget.isChecked()
            
            # 遍历设置选项卡中的所有子组件
            for child in self.settings_tab.findChildren(QCheckBox):
                # 如果找到匹配的复选框（通过文本匹配）
                if child.text() in dialog_checkboxes:
                    # 设置其状态为对话框中对应复选框的状态
                    child.setChecked(dialog_checkboxes[child.text()])
            
            # 获取选择的语言
            selected_langs = []
            # 遍历布局中的所有复选框
            for i in range(lang_options.count()):
                widget = lang_options.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget.isChecked():
                    # 从复选框标签获取语言名称，然后转换为语言代码
                    lang_name = widget.text()
                    lang_code = get_language_code(lang_name)
                    if lang_code:
                        selected_langs.append(lang_code)
            
            return selected_langs
        
        return None

    def clear_history(self):
        """清空历史记录"""
        self.download_history = []
        self.save_history()
        self.history_tab.set_history_data(self.download_history)
    
    def export_history(self):
        """导出历史记录到文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出历史记录", 
                                                  os.path.expanduser("~/Downloads/youtube_history.csv"),
                                                  "CSV文件 (*.csv)")
        if file_path:
            if self.history_manager.export_history_to_csv(file_path, self.download_history):
                QMessageBox.information(self, "导出成功", f"历史记录已导出到: {file_path}")
            else:
                QMessageBox.critical(self, "导出失败", "导出历史记录时出错")
