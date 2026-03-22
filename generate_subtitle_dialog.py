from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
)
from PyQt6.QtCore import Qt
from styles import Styles


class GenerateSubtitleDialog(QDialog):
    LANGUAGES = [
        ("自动检测", None),
        ("中文", "zh"),
        ("英文", "en"),
        ("日文", "ja"),
        ("韩文", "ko"),
        ("德文", "de"),
        ("法文", "fr"),
        ("西班牙文", "es"),
        ("葡萄牙文", "pt"),
        ("俄文", "ru"),
        ("意大利文", "it"),
        ("荷兰文", "nl"),
        ("波兰文", "pl"),
        ("土耳其文", "tr"),
        ("越南文", "vi"),
        ("泰文", "th"),
        ("阿拉伯文", "ar"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_language = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("生成字幕")
        self.setMinimumWidth(350)
        self.setStyleSheet(Styles.DARK_THEME)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 语言选择
        lang_layout = QHBoxLayout()
        lang_label = QLabel("选择语言:")
        lang_label.setMinimumWidth(80)
        self.lang_combo = QComboBox()

        for name, code in self.LANGUAGES:
            self.lang_combo.addItem(name, code)

        # 默认选择"自动检测"
        self.lang_combo.setCurrentIndex(0)

        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认")
        confirm_btn.setProperty("class", "PrimaryBtn")
        confirm_btn.clicked.connect(self.on_confirm)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def on_confirm(self):
        self.selected_language = self.lang_combo.currentData()
        self.accept()

    def get_selected_language(self):
        return self.selected_language
