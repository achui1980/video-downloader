#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, 
                            QCheckBox, QLineEdit, QLabel, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from config import Config
from download_options import DownloadSettings

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_from_config()
        self.setup_connections()
        
    def initUI(self):
        # 设置标签页布局
        settings_layout = QVBoxLayout(self)
        
        # 字幕选项
        subtitle_group = QGroupBox("字幕选项")
        
        # 在subtitle_check后添加语言选择下拉框
        subtitle_layout = QVBoxLayout()  # 改为垂直布局以便更好地组织控件
        
        subtitle_header = QHBoxLayout()
        self.subtitle_check = QCheckBox("下载视频同时下载字幕")
        subtitle_header.addWidget(self.subtitle_check)
        
        self.subtitle_lang_label = QLabel("字幕语言:")
        subtitle_header.addWidget(self.subtitle_lang_label)
        
        self.subtitle_lang_combo = QComboBox()
        self.subtitle_lang_combo.addItems(["自动", "中文", "英文", "日文"])
        subtitle_header.addWidget(self.subtitle_lang_combo)
        
        subtitle_layout.addLayout(subtitle_header)
        
        # 添加字幕语言选择组
        subtitle_only_group = QGroupBox("仅下载字幕时使用的语言选择")
        lang_options = QHBoxLayout()
        self.zh_subtitle_check = QCheckBox("中文")
        lang_options.addWidget(self.zh_subtitle_check)
        
        self.en_subtitle_check = QCheckBox("英文")
        lang_options.addWidget(self.en_subtitle_check)
        
        self.jp_subtitle_check = QCheckBox("日文")
        lang_options.addWidget(self.jp_subtitle_check)
        
        subtitle_only_group.setLayout(lang_options)
        subtitle_layout.addWidget(subtitle_only_group)
        
        subtitle_group.setLayout(subtitle_layout)
        settings_layout.addWidget(subtitle_group)
        
        # AI 翻译设置
        ai_group = QGroupBox("AI 字幕翻译设置 (ModelScope/DeepSeek)")
        ai_layout = QFormLayout()
        ai_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        ai_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setPlaceholderText("请输入 API Key (例如: ms-xxx)")
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password) # 默认密码模式
        
        # 添加眼睛图标
        self.toggle_password_action = QAction(self)
        self.toggle_password_action.setText("👁️") # 使用 emoji 代替图标文件，简化实现
        self.toggle_password_action.setToolTip("显示/隐藏 API Key")
        
        # 强制设置图标颜色为白色/亮色，以适应深色背景
        # 注意: 纯 emoji 文本无法直接改变颜色，它由系统字体渲染
        # 在深色模式下，系统 emoji 可能会难以辨认
        # 我们可以改用文本字符 'O' 或者使用 QIcon 结合 pixmap 绘制
        
        # 更好的方案：使用 Unicode 字符而非 Emoji，或者简单的 ASCII
        # 'Show' / 'Hide' 或者更通用的图标
        # 这里为了确保可见性，我们使用亮色的文本字符 'Show'
        # 并在点击时切换为 'Hide'
        self.toggle_password_action.setText("Show")
        
        # 自定义 Action 的样式比较困难，通常建议使用 QToolButton 放在 QLineEdit 旁边
        # 但 QLineEdit.addAction 很方便。
        # 让我们尝试设置 QLineEdit 的样式表来影响 action 文本颜色（但这通常只影响输入文本）
        
        self.toggle_password_action.triggered.connect(self.toggle_password_visibility)
        self.ai_api_key.addAction(self.toggle_password_action, QLineEdit.ActionPosition.TrailingPosition)
        
        ai_layout.addRow("API Key:", self.ai_api_key)
        
        self.ai_base_url = QLineEdit()
        ai_layout.addRow("Base URL:", self.ai_base_url)
        
        self.ai_model = QLineEdit()
        ai_layout.addRow("Model ID:", self.ai_model)
        
        self.ai_batch_size = QLineEdit()
        self.ai_batch_size.setPlaceholderText("每次请求翻译的行数 (默认200)")
        ai_layout.addRow("批次大小:", self.ai_batch_size)
        
        ai_group.setLayout(ai_layout)
        settings_layout.addWidget(ai_group)
        
        # 代理设置
        proxy_group = QGroupBox("代理设置")
        proxy_layout = QFormLayout()
        proxy_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        proxy_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
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
        other_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        other_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
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

    def toggle_password_visibility(self):
        """切换 API Key 的显示/隐藏状态"""
        if self.ai_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_action.setText("Hide")
        else:
            self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_action.setText("Show")

    def load_from_config(self):
        """从 Config 对象加载设置到 UI"""
        s = Config.settings
        
        # 字幕
        self.subtitle_check.setChecked(s['subtitle']['enabled'])
        self.subtitle_lang_combo.setCurrentText(s['subtitle']['language'])
        
        only_langs = s['subtitle']['only_langs']
        self.zh_subtitle_check.setChecked('zh-Hans' in only_langs)
        self.en_subtitle_check.setChecked('en' in only_langs)
        self.jp_subtitle_check.setChecked('ja' in only_langs)
        
        # AI
        self.ai_api_key.setText(s['ai_translator']['api_key'])
        self.ai_base_url.setText(s['ai_translator']['base_url'])
        self.ai_model.setText(s['ai_translator']['model'])
        self.ai_batch_size.setText(s['ai_translator']['batch_size'])
        
        # 代理
        self.proxy_check.setChecked(s['proxy']['enabled'])
        self.proxy_input.setText(s['proxy']['url'])
        self.proxy_input.setEnabled(s['proxy']['enabled'])
        
        # 其他
        self.limit_check.setChecked(s['other']['limit_speed'])
        self.limit_input.setText(s['other']['limit_rate'])
        self.limit_input.setEnabled(s['other']['limit_speed'])
        self.chrome_cookies_check.setChecked(s['other']['chrome_cookies'])

    def get_settings(self) -> DownloadSettings:
        """读取当前 UI 值，返回设置快照。替代外部直接读控件。"""
        only_langs = []
        if self.zh_subtitle_check.isChecked():
            only_langs.append('zh-Hans')
        if self.en_subtitle_check.isChecked():
            only_langs.append('en')
        if self.jp_subtitle_check.isChecked():
            only_langs.append('ja')

        batch_size = 200
        try:
            batch_size = int(self.ai_batch_size.text().strip() or "200")
        except ValueError:
            batch_size = 200

        return DownloadSettings(
            subtitle_enabled=self.subtitle_check.isChecked(),
            subtitle_language=self.subtitle_lang_combo.currentText(),
            only_langs=only_langs,
            ai_api_key=self.ai_api_key.text().strip(),
            ai_base_url=self.ai_base_url.text().strip(),
            ai_model=self.ai_model.text().strip(),
            ai_batch_size=batch_size,
            proxy_enabled=self.proxy_check.isChecked(),
            proxy_url=self.proxy_input.text().strip(),
            limit_speed=self.limit_check.isChecked(),
            limit_rate=self.limit_input.text().strip(),
            chrome_cookies=self.chrome_cookies_check.isChecked(),
        )

    def setup_connections(self):
        """连接信号到保存配置逻辑"""
        # 字幕
        self.subtitle_check.toggled.connect(self.save_to_config)
        self.subtitle_lang_combo.currentTextChanged.connect(self.save_to_config)
        self.zh_subtitle_check.toggled.connect(self.save_to_config)
        self.en_subtitle_check.toggled.connect(self.save_to_config)
        self.jp_subtitle_check.toggled.connect(self.save_to_config)
        
        # AI
        self.ai_api_key.textChanged.connect(self.save_to_config)
        self.ai_base_url.textChanged.connect(self.save_to_config)
        self.ai_model.textChanged.connect(self.save_to_config)
        self.ai_batch_size.textChanged.connect(self.save_to_config)
        
        # 代理
        self.proxy_check.toggled.connect(self.save_to_config)
        self.proxy_input.textChanged.connect(self.save_to_config)
        
        # 其他
        self.limit_check.toggled.connect(self.save_to_config)
        self.limit_input.textChanged.connect(self.save_to_config)
        self.chrome_cookies_check.toggled.connect(self.save_to_config)

    def save_to_config(self):
        """将 UI 设置保存到 Config 对象并写入文件"""
        s = Config.settings
        
        # 字幕
        s['subtitle']['enabled'] = self.subtitle_check.isChecked()
        s['subtitle']['language'] = self.subtitle_lang_combo.currentText()
        
        only_langs = []
        if self.zh_subtitle_check.isChecked(): only_langs.append('zh-Hans')
        if self.en_subtitle_check.isChecked(): only_langs.append('en')
        if self.jp_subtitle_check.isChecked(): only_langs.append('ja')
        s['subtitle']['only_langs'] = only_langs
        
        # AI
        s['ai_translator']['api_key'] = self.ai_api_key.text()
        s['ai_translator']['base_url'] = self.ai_base_url.text()
        s['ai_translator']['model'] = self.ai_model.text()
        s['ai_translator']['batch_size'] = self.ai_batch_size.text()
        
        # 代理
        s['proxy']['enabled'] = self.proxy_check.isChecked()
        s['proxy']['url'] = self.proxy_input.text()
        
        # 其他
        s['other']['limit_speed'] = self.limit_check.isChecked()
        s['other']['limit_rate'] = self.limit_input.text()
        s['other']['chrome_cookies'] = self.chrome_cookies_check.isChecked()
        
        # 触发持久化
        Config.save_config()
