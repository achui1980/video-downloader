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

from download_thread import DownloadThread, AnalyzeThread
from custom_events import ShowMessageEvent, UpdateStatusEvent, UpdateVideoInfoEvent, handle_custom_event
from utils import format_duration, format_size, format_time
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
        
    def initUI(self):
        self.setWindowTitle('YouTube 视频下载器')
        self.setGeometry(100, 100, 900, 600)
        
        # 创建主窗口部件和布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 下载按钮
        download_label = QLabel("下载")
        toolbar_layout.addWidget(download_label)
        
        # 格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItems(["最佳质量", "仅视频", "仅音频 (MP3)", "1080p", "720p", "480p", "360p"])
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
        
        self.download_path = QLineEdit()
        self.download_path.setText(os.path.expanduser("~/Movies/yt-dlp"))
        toolbar_layout.addWidget(self.download_path)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_folder)
        toolbar_layout.addWidget(self.browse_btn)
        
        main_layout.addLayout(toolbar_layout)
        
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
        settings_layout = QVBoxLayout(self.settings_tab)
        
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
        
        # if 'formats' in info:
        #     info_text += "可用格式:\n"
        #     for fmt in info['formats']:
        #         format_note = fmt.get('format_note', '')
        #         if format_note:
        #             resolution = fmt.get('resolution', 'N/A')
        #             ext = fmt.get('ext', 'N/A')
        #             info_text += f"- {format_note} ({resolution}, {ext})\n"
        
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
        
        # 准备下载选项
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        }
        
        # 格式选择
        format_option = self.format_combo.currentText()
        if format_option == "最佳质量":
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "仅视频":
            ydl_opts['format'] = 'bestvideo/best'
        elif format_option == "仅音频 (MP3)":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_option == "1080p":
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "720p":
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "480p":
            ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "360p":
            ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best[height<=360]'
            ydl_opts['merge_output_format'] = 'mp4'
        
        # 字幕选项
        if self.settings_tab.subtitle_check.isChecked():
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
        
        # 速度限制选项
        if self.settings_tab.limit_check.isChecked() and self.settings_tab.limit_input.text().strip():
            ydl_opts['ratelimit'] = self.settings_tab.limit_input.text().strip()
        
        # 代理选项
        if self.settings_tab.proxy_check.isChecked() and self.settings_tab.proxy_input.text().strip():
            ydl_opts['proxy'] = self.settings_tab.proxy_input.text().strip()
            
        # 添加Chrome浏览器Cookies选项
        if hasattr(self.settings_tab, 'chrome_cookies_check') and self.settings_tab.chrome_cookies_check.isChecked():
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
        
        # 创建下载线程
        download_thread = DownloadThread(url, ydl_opts)
        download_thread.progress_signal.connect(self.update_progress)
        download_thread.complete_signal.connect(self.download_complete)
        download_thread.error_signal.connect(self.download_error)
        
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
        
        # 从下载信息中获取实际文件路径和其他信息
        title = info.get('title', '未知')
        duration = format_duration(info.get('duration', 0))
        size = '未知'
        resolution = '未知'
        uploader = info.get('uploader', '未知')
        
        if info and 'requested_downloads' in info:
            # 从请求的下载列表中获取第一个文件
            download_info = info['requested_downloads'][0] if info['requested_downloads'] else None
            if download_info:
                if 'filepath' in download_info:
                    # 使用实际下载的文件路径
                    filepath = download_info['filepath']
                    # 从文件路径中提取文件名（不含扩展名）
                    title = os.path.splitext(os.path.basename(filepath))[0]
                
                # 获取文件大小
                if 'filesize' in download_info and download_info['filesize']:
                    size = format_size(download_info['filesize'])
                elif 'filesize_approx' in download_info and download_info['filesize_approx']:
                    size = format_size(download_info['filesize_approx'])
                
                # 获取分辨率
                if 'resolution' in download_info and download_info['resolution']:
                    resolution = download_info['resolution']
                elif 'height' in download_info and download_info['height']:
                    resolution = f"{download_info['height']}p"
        
        # 创建更详细的历史记录项
        history_item = {
            'title': title,
            'url': url,
            'format': format_option,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration': duration,
            'size': size,
            'resolution': resolution,
            'uploader': uploader
        }
        
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
    
    def cancel_download(self):
        url = self.url_input.text().strip()
        if url in self.download_threads:
            self.download_threads[url].cancel()
            self.status_label.setText("正在取消...")