# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from task_widget import TaskWidget


class TasksPage(QWidget):
    """当前任务页：负责 TaskWidget 容器，不持有下载线程。"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("当前任务")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        self.tasks_container_layout = QVBoxLayout(scroll_content)
        self.tasks_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tasks_container_layout.setSpacing(10)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def add_task_widget(self, url) -> TaskWidget:
        widget = TaskWidget(url, title=f"正在解析: {url}")
        self.tasks_container_layout.addWidget(widget)
        return widget

    def remove_task_widget(self, widget: TaskWidget):
        self.tasks_container_layout.removeWidget(widget)
        widget.deleteLater()
