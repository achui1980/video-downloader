from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from utils import format_size, format_time

class TaskWidget(QFrame):
    cancel_requested = pyqtSignal()

    def __init__(self, url, title="正在分析...", parent=None):
        super().__init__(parent)
        self.setObjectName("TaskWidget")
        self.url = url
        self.initUI(title)

    def initUI(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header: Title and Cancel Button
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TaskTitle")
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label, stretch=1)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(60, 24)
        self.cancel_btn.setStyleSheet("background-color: #d32f2f; font-size: 12px; padding: 2px;")
        self.cancel_btn.clicked.connect(self.request_cancel)
        header_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(header_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        # Status Info (Size, Speed, ETA)
        self.status_label = QLabel("准备下载...")
        self.status_label.setObjectName("TaskStatus")
        layout.addWidget(self.status_label)

    def update_progress(self, progress_data):
        downloaded = progress_data.get('downloaded_bytes', 0)
        total = progress_data.get('total_bytes', 0) or progress_data.get('total_bytes_estimate', 0)
        
        if total and total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
            
            speed = progress_data.get('speed', 0)
            eta = progress_data.get('eta', 0)
            
            status_text = f"{format_size(downloaded)} / {format_size(total)}"
            if speed:
                status_text += f" • {format_size(speed)}/s"
            if eta:
                status_text += f" • 剩余: {format_time(eta)}"
            
            self.status_label.setText(status_text)
        else:
            self.progress_bar.setRange(0, 0) # Indeterminate
            self.status_label.setText(f"已下载: {format_size(downloaded)}")

    def set_status(self, message):
        self.status_label.setText(message)

    def set_title(self, title):
        self.title_label.setText(title)

    def set_finished(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText("下载完成")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("完成")
        self.cancel_btn.setStyleSheet("background-color: #388e3c; font-size: 12px; padding: 2px;")

    def set_error(self, message):
        self.status_label.setText(f"错误: {message}")
        self.status_label.setStyleSheet("color: #ff5252;")
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff5252; }")
        self.cancel_btn.setText("重试") # Future improvement: retry logic
        self.cancel_btn.setEnabled(True)

    def set_cancelled(self):
        self.status_label.setText("已取消")
        self.progress_bar.setValue(0)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("已取消")
        self.cancel_btn.setStyleSheet("background-color: #616161; font-size: 12px; padding: 2px;")

    def request_cancel(self):
        self.cancel_requested.emit()
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("正在取消...")
