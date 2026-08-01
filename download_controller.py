# -*- coding: utf-8 -*-

import os

from PyQt6.QtCore import QObject, pyqtSignal

from download_manager import DownloadManager
from download_options import DownloadOptions
from download_thread import DownloadThread
from pages.tasks_page import TasksPage


class DownloadController(QObject):
    """下载编排：持有线程与 TaskWidget，通过信号向上层（ui.py）汇报。"""

    active_count_changed = pyqtSignal(int)
    history_item_completed = pyqtSignal(dict, str)  # info, format_option

    def __init__(self, tasks_page: TasksPage, parent=None):
        super().__init__(parent)
        self.tasks_page = tasks_page
        self.download_threads = {}
        self.active_tasks = {}

    def has_active(self, url) -> bool:
        return url in self.download_threads

    def start(self, options: DownloadOptions):
        url = options.url
        if url in self.download_threads:
            self._cancel_existing(url)

        ydl_opts = DownloadManager.prepare_download_options(
            options.format,
            options.download_path,
            options.subtitle,
            options.speed_limit,
            options.proxy,
            options.use_chrome_cookies,
            enable_logging=True,
            url=url,
        )

        task_widget = self.tasks_page.add_task_widget(url)
        self.active_tasks[url] = task_widget

        thread = DownloadThread(url, ydl_opts)
        thread.progress_signal.connect(task_widget.update_progress)
        thread.complete_signal.connect(
            lambda info, fmt=options.format: self._on_complete(url, info, fmt)
        )
        thread.error_signal.connect(task_widget.set_error)
        thread.error_signal.connect(lambda msg: self.cleanup(url))
        thread.cancelled_signal.connect(task_widget.set_cancelled)
        thread.cancelled_signal.connect(lambda: self.cleanup(url))
        task_widget.cancel_requested.connect(lambda: self.cancel(url))

        self.download_threads[url] = thread
        thread.start()
        self.active_count_changed.emit(len(self.download_threads))

    def _cancel_existing(self, url):
        thread = self.download_threads[url]
        if thread.isRunning():
            thread.cancel()
            thread.wait()
        old_widget = self.active_tasks.get(url)
        if old_widget:
            self.tasks_page.remove_task_widget(old_widget)
            del self.active_tasks[url]

    def _on_complete(self, url, info, format_option):
        task_widget = self.active_tasks.get(url)
        if task_widget:
            task_widget.set_title(info.get("title", "未知"))
            task_widget.set_finished()
        self.history_item_completed.emit(info, format_option)
        self.cleanup(url)

    def cancel(self, url):
        thread = self.download_threads.get(url)
        if thread:
            thread.cancel()

    def cleanup(self, url):
        self.download_threads.pop(url, None)
        self.active_count_changed.emit(len(self.download_threads))

    def close_all(self):
        for thread in self.download_threads.values():
            thread.cancel()
