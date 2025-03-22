#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui import YoutubeDownloader

def resource_path(relative_path):
    """获取资源绝对路径，用于处理 PyInstaller 打包后的路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 创建的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 正常情况下的路径
    return os.path.join(os.path.abspath("."), relative_path)

def main():
    """应用程序入口点"""
    app = QApplication(sys.argv)
    
    # 设置应用图标
    icon_path = resource_path(os.path.join('assets', 'icon.ico'))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建并显示主窗口
    window = YoutubeDownloader()
    window.show()
    
    # 运行应用循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()