#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox
import yt_dlp
import sys

from custom_events import ShowMessageEvent, UpdateStatusEvent, UpdateVideoInfoEvent
from download import YouTubeDownloader

class DownloadThread(QThread):
    progress_signal = pyqtSignal(dict)
    complete_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    cancelled_signal = pyqtSignal()  # 新增取消信号
    
    def __init__(self, url, options):
        super().__init__()
        self.url = url
        self.options = options
        self.is_cancelled = False
        self.ydl = None
        
    def run(self):
        try:
            # 添加取消检查的钩子函数
            self.options['progress_hooks'] = [self.progress_hook]
            
            # 添加下载前检查
            if self.is_cancelled:
                self.cancelled_signal.emit()
                return
                
            # 创建yt-dlp下载器实例
            self.ydl = yt_dlp.YoutubeDL(self.options)
            
            # 使用下载器类下载视频
            info = self.ydl.extract_info(self.url, download=True)
            
            # 完成下载后再次检查是否被取消
            if not self.is_cancelled:
                self.complete_signal.emit(info)
            else:
                self.cancelled_signal.emit()
        except Exception as e:
            if self.is_cancelled:
                self.cancelled_signal.emit()
            else:
                self.error_signal.emit(str(e))
    
    def progress_hook(self, progress):
        # 每次进度更新时检查是否取消
        if self.is_cancelled:
            # 抛出异常以中断下载过程
            raise yt_dlp.utils.DownloadCancelled("下载已取消")
        
        if progress['status'] == 'downloading':
            self.progress_signal.emit(progress)
    
    def cancel(self):
        # 设置取消标志
        self.is_cancelled = True
        
        # 如果ydl实例已创建，尝试中断它
        if self.ydl:
            # 尝试直接终止下载
            if hasattr(self.ydl, '_finish_multiline_status'):
                try:
                    self.ydl._finish_multiline_status()
                except:
                    print("下载器实例无法终止")
                    pass
        
        # 确保信号在主线程中发送
        QApplication.processEvents()
        
        # 强制终止线程
        self.terminate()
        self.wait(1000)  # 等待最多1秒让线程结束
        
        # 确保取消信号被发送
        self.cancelled_signal.emit()


# 分析线程类
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
            # 使用YouTubeDownloader类分析视频
            info = YouTubeDownloader.extract_info(self.url, self.ydl_opts, download=False)
            self.info_ready_signal.emit(info)
        except Exception as e:
            self.error_signal.emit(f"分析视频时出错: {str(e)}")