#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                            QCheckBox, QLineEdit)
from PyQt6.QtCore import Qt

class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.initUI()
        
    def initUI(self):
        # 设置标签页布局
        settings_layout = QVBoxLayout(self)
        
        # 字幕选项
        subtitle_group = QGroupBox("字幕选项")
        subtitle_layout = QFormLayout()
        
        self.subtitle_check = QCheckBox("下载字幕")
        subtitle_layout.addRow("", self.subtitle_check)
        
        subtitle_group.setLayout(subtitle_layout)
        settings_layout.addWidget(subtitle_group)
        
        # 代理设置
        proxy_group = QGroupBox("代理设置")
        proxy_layout = QFormLayout()
        
        self.proxy_check = QCheckBox("使用代理")
        proxy_layout.addRow("", self.proxy_check)
        
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://proxy.example.com:8080")
        self.proxy_input.setEnabled(False)
        proxy_layout.addRow("代理地址:", self.proxy_input)
        
        self.proxy_check.toggled.connect(lambda checked: self.proxy_input.setEnabled(checked))
        
        proxy_group.setLayout(proxy_layout)
        settings_layout.addWidget(proxy_group)
        
        # 其他设置
        other_group = QGroupBox("其他设置")
        other_layout = QFormLayout()
        
        self.limit_check = QCheckBox("限制下载速度")
        other_layout.addRow("", self.limit_check)
        
        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("1M")
        self.limit_input.setEnabled(False)
        other_layout.addRow("速度限制:", self.limit_input)
        
        self.limit_check.toggled.connect(lambda checked: self.limit_input.setEnabled(checked))
        
        # 添加Chrome浏览器Cookies选项
        self.chrome_cookies_check = QCheckBox("使用Chrome浏览器Cookies")
        self.chrome_cookies_check.setToolTip("从Chrome浏览器获取Cookies，用于下载需要登录的视频")
        other_layout.addRow("", self.chrome_cookies_check)
        
        other_group.setLayout(other_layout)
        settings_layout.addWidget(other_group)
        
        settings_layout.addStretch(1)