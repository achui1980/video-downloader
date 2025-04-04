#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import threading
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QProgressBar, QComboBox,
                             QCheckBox, QFileDialog, QMessageBox, QTabWidget, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout,
                             QApplication)
from PyQt6.QtCore import Qt, QSize, QMetaObject, QThread
from PyQt6.QtGui import QIcon, QFont
import yt_dlp

from download import YouTubeDownloader
from download_thread import DownloadThread, AnalyzeThread
from custom_events import ShowMessageEvent, UpdateStatusEvent, UpdateVideoInfoEvent, handle_custom_event
from utils import format_duration, format_size, format_time, get_language_code
from history_manager import HistoryManager
from tabs.history_tab import HistoryTab
from tabs.settings_tab import SettingsTab


class YoutubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_threads = {}
        self.download_history = []
        
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
            app_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(app_dir, 'logs')
        
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建应用程序日志文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'app_{timestamp}.log')
        
        # 初始化日志记录器
        from my_logger import MyLogger
        self.logger = MyLogger.get_instance(log_file)
        
        # 记录应用程序启动信息
        self.logger.info(f"应用程序启动于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # self.logger.info(f"应用程序目录: {app_dir}")
        self.logger.info(f"日志目录: {log_dir}")
        
    def initUI(self):
        self.setWindowTitle('YouTube 视频下载器')
        self.setGeometry(100, 100, 900, 600)
        
        # 创建主窗口部件和布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 下载按钮
        app_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(app_dir, 'logs')
        download_label = QLabel(f"下载")
        toolbar_layout.addWidget(download_label)
        
        # 格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItems(["最佳质量", "仅视频", "仅音频 (MP3)", "仅字幕", "1080p", "720p", "480p", "360p"])
        toolbar_layout.addWidget(self.format_combo)
        
        # 为系统选择
        for_label = QLabel("为")
        toolbar_layout.addWidget(for_label)
        
        self.system_combo = QComboBox()
        self.system_combo.addItems(["Mac OS", "Windows", "Linux"])
        self.system_combo.setCurrentText("Mac OS")
        toolbar_layout.addWidget(self.system_combo)
        
        # 保存到选择
        save_to_label = QLabel("保存到")
        toolbar_layout.addWidget(save_to_label)
        
        download_path = os.path.expanduser("~/Movies/yt-dlp")
        self.download_path = QLineEdit()
        self.download_path.setText(download_path)
        toolbar_layout.addWidget(self.download_path)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_folder)
        toolbar_layout.addWidget(self.browse_btn)
        
        main_layout.addLayout(toolbar_layout)

         # 初始化日志系统
        log_dir = os.path.join(download_path, 'logs')
        self.init_logger(log_dir)
        
        # URL输入区域
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入YouTube视频URL...")
        self.url_input.setText("https://www.youtube.com/shorts/RIrEOv7sXYo")
        url_layout.addWidget(self.url_input)
        
        self.analyze_btn = QPushButton("分析")
        self.analyze_btn.clicked.connect(self.analyze_url)
        url_layout.addWidget(self.analyze_btn)
        
        main_layout.addLayout(url_layout)
        
        # 创建标签页
        tabs = QTabWidget()
        all_tab = QWidget()
        self.history_tab = HistoryTab(self)
        self.settings_tab = SettingsTab(self)
        
        tabs.addTab(all_tab, "全部")
        tabs.addTab(self.history_tab, "历史记录")
        tabs.addTab(self.settings_tab, "设置")
        
        # 全部标签页布局
        all_layout = QVBoxLayout(all_tab)
        
        # 视频信息区域
        self.video_info = QTextEdit()
        self.video_info.setReadOnly(True)
        self.video_info.setMaximumHeight(100)
        all_layout.addWidget(self.video_info)
        
        # 创建下载列表表格
        self.download_table = QTableWidget(0, 7)
        self.download_table.setHorizontalHeaderLabels(["", "标题", "时长", "大小", "格式", "分辨率", "来源"])
        self.download_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 标题列自适应
        self.download_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 设置列宽
        self.download_table.setColumnWidth(0, 40)  # 图标列
        self.download_table.setColumnWidth(2, 80)  # 时长列
        self.download_table.setColumnWidth(3, 80)  # 大小列
        self.download_table.setColumnWidth(4, 80)  # 格式列
        self.download_table.setColumnWidth(5, 80)  # 分辨率列
        self.download_table.setColumnWidth(6, 150)  # 来源列
        
        all_layout.addWidget(self.download_table)
        
        # 下载按钮和进度条
        action_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("下载")
        self.download_btn.clicked.connect(self.start_download)
        action_layout.addWidget(self.download_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        action_layout.addWidget(self.cancel_btn)
        
        all_layout.addLayout(action_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        all_layout.addWidget(self.progress_bar)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("准备就绪")
        status_layout.addWidget(self.status_label)
        
        all_layout.addLayout(status_layout)
        
        # 设置标签页
        # settings_layout = QVBoxLayout(self.settings_tab)
        
        main_layout.addWidget(tabs)
        self.setCentralWidget(main_widget)
        
        # 填充示例数据到下载表格
        self.populate_example_data()
    
    def populate_example_data(self):
        """填充示例数据到下载表格"""
        # 清空表格
        self.download_table.setRowCount(0)
        
        # 添加到表格
        for item in self.download_history:
            row = self.download_table.rowCount()
            self.download_table.insertRow(row)
            
            # 添加播放图标
            play_btn = QPushButton("▶")
            play_btn.setMaximumWidth(30)
            play_btn.clicked.connect(lambda checked, item=item: self.play_item(item))
            self.download_table.setCellWidget(row, 0, play_btn)
            
            # 添加其他数据
            self.download_table.setItem(row, 1, QTableWidgetItem(item.get('title', '未知')))
            self.download_table.setItem(row, 2, QTableWidgetItem(item.get('duration', '--:--')))
            self.download_table.setItem(row, 3, QTableWidgetItem(item.get('size', '未知')))
            self.download_table.setItem(row, 4, QTableWidgetItem(item.get('format', '未知')))
            self.download_table.setItem(row, 5, QTableWidgetItem(item.get('resolution', '未知')))
            self.download_table.setItem(row, 6, QTableWidgetItem(item.get('uploader', '未知')))
    
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
        
        # 准备分析选项
        ydl_opts = {}
        
        # 添加Chrome浏览器Cookies选项
        if hasattr(self, 'chrome_cookies_check') and self.chrome_cookies_check.isChecked():
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
        
        # 创建分析线程
        self.analyze_thread = AnalyzeThread(self, url, ydl_opts)
        
        # 连接信号到槽函数
        self.analyze_thread.info_ready_signal.connect(self.update_video_info)
        self.analyze_thread.error_signal.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
        self.analyze_thread.status_signal.connect(self.status_label.setText)
        
        # 启动线程
        self.analyze_thread.start()
    
    def update_video_info(self, info):
        if not info:
            return
            
        info_text = f"标题: {info.get('title', '未知')}\n"
        info_text += f"上传者: {info.get('uploader', '未知')}\n"
        info_text += f"时长: {format_duration(info.get('duration', 0))}\n"
        info_text += f"上传日期: {info.get('upload_date', '未知')}\n\n"
        
        # 添加字幕语言支持信息
        if 'subtitles' in info and info['subtitles']:
            available_subtitles = info['subtitles'].keys()
            info_text += "字幕支持:\n"
            
            # 获取设置选项卡中配置的字幕语言
            supported_languages = []
            for child in self.settings_tab.findChildren(QCheckBox):
                lang_name = child.text()
                lang_code = get_language_code(lang_name)
                if lang_code:
                    is_supported = lang_code in available_subtitles
                    supported_languages.append(f"- {lang_name}: {'✓' if is_supported else '✗'}")
            
            # 如果没有找到配置的语言，显示所有可用的字幕
            if not supported_languages:
                for lang_code in available_subtitles:
                    supported_languages.append(f"- {lang_code}")
            
            info_text += "\n".join(supported_languages) + "\n"
        else:
            info_text += "字幕支持: 无\n"
        
        self.video_info.setText(info_text)
        self.status_label.setText("分析完成")
        

# Remove the update_video_info method since we're handling this in the custom event handler
    
    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入有效的URL")
            return
        
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
        
        # 使用YouTubeDownloader来准备下载选项
        format_option = self.format_combo.currentText()
        if format_option == "仅字幕":
            selected_langs = self.show_subtitle_options_dialog()
            if not selected_langs:
                return  # 用户取消了操作
            else:
                subtitle_options = {
                    'languages': selected_langs
                }
        
        ydl_opts = YouTubeDownloader.prepare_download_options(
            format_option, 
            download_path, 
            subtitle_options, 
            limit, 
            proxy, 
            use_chrome_cookies,
            enable_logging=True,
            url=url
        )
        
        # 创建下载线程
        download_thread = DownloadThread(url, ydl_opts)
        download_thread.progress_signal.connect(self.update_progress)
        download_thread.complete_signal.connect(self.download_complete)
        download_thread.error_signal.connect(self.download_error)
        download_thread.cancelled_signal.connect(self.download_cancelled)  
        
        # 保存线程引用
        self.download_threads[url] = download_thread
        
        # 更新UI状态
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_label.setText("正在下载...")
        self.progress_bar.setValue(0)
        
        # 启动下载线程
        download_thread.start()
    
    def update_progress(self, progress_data):
        try:
            downloaded = progress_data.get('downloaded_bytes', 0)
            total = progress_data.get('total_bytes', 0) or progress_data.get('total_bytes_estimate', 0)
            
            # 确保 total 不为 None 且大于 0
            if total is not None and total > 0:
                percent = int(downloaded * 100 / total)
                self.progress_bar.setValue(percent)
                
                # 更新状态标签显示下载速度和进度
                speed = progress_data.get('speed', 0)
                eta = progress_data.get('eta', 0)
                
                status_text = f"下载中: {format_size(downloaded)}/{format_size(total)} "
                if speed is not None and speed > 0:
                    status_text += f"- {format_size(speed)}/s "
                if eta is not None and eta > 0:
                    status_text += f"- 剩余时间: {format_time(eta)}"
                
                self.status_label.setText(status_text)
            else:
                # 如果没有总大小信息，显示已下载的大小
                status_text = f"下载中: {format_size(downloaded)} (未知总大小) "
                speed = progress_data.get('speed', 0)
                if speed is not None and speed > 0:
                    status_text += f"- {format_size(speed)}/s"
                self.status_label.setText(status_text)
        except Exception as e:
            print(f"更新进度时出错: {str(e)}")
    
    def load_history(self):
        """加载历史记录"""
        self.download_history = self.history_manager.load_history()
    
    def save_history(self):
        """保存历史记录到文件"""
        self.history_manager.save_history(self.download_history)
    
    
    def download_complete(self, info):
        url = self.url_input.text().strip()
        format_option = self.format_combo.currentText()
        
        # 使用YouTubeDownloader获取下载结果信息
        history_item = YouTubeDownloader.get_download_info_from_result(info, format_option)
        
        # 添加时间戳
        history_item['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加到表格
        row = self.history_tab.history_table.rowCount()
        self.history_tab.history_table.insertRow(row)
        
        # 添加播放图标
        play_btn = QPushButton("▶")
        play_btn.setMaximumWidth(30)
        self.history_tab.history_table.setCellWidget(row, 0, play_btn)
        
        # 添加其他数据
        self.history_tab.history_table.setItem(row, 1, QTableWidgetItem(history_item['title']))
        self.history_tab.history_table.setItem(row, 2, QTableWidgetItem(history_item['duration']))
        self.history_tab.history_table.setItem(row, 3, QTableWidgetItem(history_item['size']))
        self.history_tab.history_table.setItem(row, 4, QTableWidgetItem(history_item['format']))
        self.history_tab.history_table.setItem(row, 5, QTableWidgetItem(history_item['resolution']))
        self.history_tab.history_table.setItem(row, 6, QTableWidgetItem(history_item['uploader']))
        
        # 保存到历史记录列表
        self.download_history.append(history_item)
        
        # 保存历史记录到文件
        self.save_history()
        
        # 更新历史记录表格
        self.history_tab.populate_history_table()
        self.populate_example_data()
        
        # 更新UI状态
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("下载完成")
        self.progress_bar.setValue(100)
        
        # 清理线程引用
        if url in self.download_threads:
            del self.download_threads[url]
    
    # 添加关闭事件处理，确保退出前保存历史记录
    def closeEvent(self, event):
        self.save_history()
        event.accept()
        
        # 更新UI状态
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("下载失败")
        
        # 清理线程引用
        url = self.url_input.text().strip()
        if url in self.download_threads:
            del self.download_threads[url]
    
    def download_error(self, error_msg):
        """处理下载错误"""
        QMessageBox.critical(self, "下载错误", error_msg)
        
        # 更新UI状态
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("下载失败")
        
        # 清理线程引用
        url = self.url_input.text().strip()
        if url in self.download_threads:
            del self.download_threads[url]
    
    def download_cancelled(self):
        """处理下载取消的情况"""
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("下载已取消")
        self.progress_bar.setValue(0)
        
        # 清理线程引用
        url = self.url_input.text().strip()
        if url in self.download_threads:
            del self.download_threads[url]
    
    def cancel_download(self):
        url = self.url_input.text().strip()
        if url in self.download_threads:
            self.status_label.setText("正在取消...")
            self.download_threads[url].cancel()
            # 不在这里删除线程引用和重置UI状态，就是在cancelled_signal处理中进行

    def show_subtitle_options_dialog(self):
        """显示字幕选项对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("选择字幕语言")
        dialog.setMinimumWidth(300)
        
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