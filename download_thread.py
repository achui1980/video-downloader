#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox
import yt_dlp

from custom_events import ShowMessageEvent, UpdateStatusEvent, UpdateVideoInfoEvent

# 移除 HistoryManager 类，它现在在单独的文件中
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
            # Add progress hooks
            self.options['progress_hooks'] = [self.progress_hook]
            
            # Create a downloader
            with yt_dlp.YoutubeDL(self.options) as ydl:
                info = ydl.extract_info(self.url, download=True)
                if not self.is_cancelled:
                    self.complete_signal.emit(info)
        except Exception as e:
            if not self.is_cancelled:
                self.error_signal.emit(str(e))
    
    def progress_hook(self, progress):
        if self.is_cancelled:
            raise Exception("Download cancelled")
        
        if progress['status'] == 'downloading':
            self.progress_signal.emit(progress)
    
    def cancel(self):
        self.is_cancelled = True

# 新增分析线程类
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
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                self.status_signal.emit("正在获取视频信息...")
                info = ydl.extract_info(self.url, download=False)
                self.info_ready_signal.emit(info)
        except Exception as e:
            self.error_signal.emit(f"分析视频时出错: {str(e)}")