#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui import YoutubeDownloader


def resource_path(relative_path):
    """获取资源绝对路径，用于处理 PyInstaller 打包后的路径"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 创建的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 正常情况下的路径
    return os.path.join(os.path.abspath("."), relative_path)


def _setup_frozen_paths():
    """冻结态下将随包分发的 ffmpeg/ffprobe 目录注入 PATH。"""
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        ffmpeg_dir = os.path.join(bundle_dir, "ffmpeg")
        if os.path.isdir(ffmpeg_dir):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


def main():
    """应用程序入口点"""
    _setup_frozen_paths()
    app = QApplication(sys.argv)

    # 设置应用名称
    app.setApplicationDisplayName("YT Downloader")

    # 设置应用图标
    icon_path = resource_path(os.path.join("assets", "icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 创建并显示主窗口
    window = YoutubeDownloader()
    window.show()

    # 运行应用循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
