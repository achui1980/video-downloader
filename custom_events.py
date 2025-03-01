#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QEvent
from utils import format_duration, format_size, format_time

# 自定义事件类型
class ShowMessageEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())  # PyQt6 中的变化
    
    def __init__(self, title, message, icon):
        super().__init__(self.EVENT_TYPE)
        self.title = title
        self.message = message
        self.icon = icon
    
    def type(self):
        return self.EVENT_TYPE

class UpdateStatusEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())  # PyQt6 中的变化
    
    def __init__(self, status):
        super().__init__(self.EVENT_TYPE)
        self.status = status
    
    def type(self):
        return self.EVENT_TYPE

class UpdateVideoInfoEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())  # PyQt6 中的变化
    
    def __init__(self, info):
        super().__init__(self.EVENT_TYPE)
        self.info = info
    
    def type(self):
        return self.EVENT_TYPE

# 自定义事件处理方法
def handle_custom_event(self, event):
    if event.type() == ShowMessageEvent.EVENT_TYPE:
        QMessageBox.warning(self, event.title, event.message, event.icon)
        return True
    elif event.type() == UpdateStatusEvent.EVENT_TYPE:
        self.status_label.setText(event.status)
        return True
    elif event.type() == UpdateVideoInfoEvent.EVENT_TYPE:
        # 在主线程中处理视频信息更新
        info = event.info
        if not info:
            return True
            
        info_text = f"标题: {info.get('title', '未知')}\n"
        info_text += f"上传者: {info.get('uploader', '未知')}\n"
        # 使用导入的 format_duration 而不是 self.format_duration
        info_text += f"时长: {format_duration(info.get('duration', 0))}\n"
        info_text += f"上传日期: {info.get('upload_date', '未知')}\n\n"
        
        if 'formats' in info:
            info_text += "可用格式:\n"
            for fmt in info['formats']:
                format_note = fmt.get('format_note', '')
                if format_note:
                    resolution = fmt.get('resolution', 'N/A')
                    ext = fmt.get('ext', 'N/A')
                    info_text += f"- {format_note} ({resolution}, {ext})\n"
        
        self.video_info.setText(info_text)
        self.status_label.setText("分析完成")
        return True
    return False