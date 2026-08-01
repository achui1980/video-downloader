# -*- coding: utf-8 -*-

import threading
import yt_dlp


class DownloadCancelled(Exception):
    """内部取消信号，非 yt-dlp 异常"""
    pass


class DownloadWorker:
    """纯 Python 下载 worker，无 Qt 依赖。GUI 用 DownloadThread 包装，API 服务直接使用。"""

    def __init__(self, url, options, on_progress=None, on_complete=None, on_error=None):
        self.url = url
        self.options = dict(options)
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self._cancelled = threading.Event()
        self.done = threading.Event()
        self.ydl = None

    def cancel(self):
        """请求取消下载"""
        self._cancelled.set()

    @property
    def cancelled(self):
        return self._cancelled.is_set()

    def _progress_hook(self, d):
        if self._cancelled.is_set():
            raise yt_dlp.utils.DownloadCancelled("下载已取消")
        if d["status"] == "downloading" and self.on_progress:
            self.on_progress(d)

    def run(self):
        try:
            if self._cancelled.is_set():
                raise DownloadCancelled("下载已取消")

            self.options["progress_hooks"] = [self._progress_hook]
            self.ydl = yt_dlp.YoutubeDL(self.options)
            info = self.ydl.extract_info(self.url, download=True)

            if self._cancelled.is_set():
                raise DownloadCancelled("下载已取消")

            if self.on_complete:
                self.on_complete(info)
        except (DownloadCancelled, yt_dlp.utils.DownloadCancelled):
            if self.on_error:
                self.on_error("cancelled")
        except Exception as e:
            if self._cancelled.is_set():
                if self.on_error:
                    self.on_error("cancelled")
            elif self.on_error:
                self.on_error(str(e))
        finally:
            self.done.set()
