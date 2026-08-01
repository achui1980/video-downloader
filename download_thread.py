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
