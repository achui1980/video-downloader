#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
                            QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCursor
import os
from datetime import datetime

class HistoryTab(QWidget):
    request_clear_history = pyqtSignal()
    request_export_history = pyqtSignal()
    request_merge_subtitle = pyqtSignal(str, str) # video_path, subtitle_path
    request_translate_subtitle = pyqtSignal(str) # subtitle_path
    
    def __init__(self):
        super().__init__()
        self.history_data = []
        self.initUI()
        
    def initUI(self):
        # 历史记录标签页布局
        history_layout = QVBoxLayout(self)
        
        # 创建历史记录表格
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["", "标题", "时长", "大小", "格式", "分辨率", "来源"])
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 标题列自适应
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 设置列宽
        self.history_table.setColumnWidth(0, 40)  # 图标列
        self.history_table.setColumnWidth(2, 80)  # 时长列
        self.history_table.setColumnWidth(3, 80)  # 大小列
        self.history_table.setColumnWidth(4, 80)  # 格式列
        self.history_table.setColumnWidth(5, 80)  # 分辨率列
        self.history_table.setColumnWidth(6, 150)  # 来源列
        
        history_layout.addWidget(self.history_table)
        
        # 添加历史记录操作按钮
        history_buttons_layout = QHBoxLayout()
        
        self.clear_history_btn = QPushButton("清空历史")
        self.clear_history_btn.clicked.connect(self.clear_history)
        history_buttons_layout.addWidget(self.clear_history_btn)
        
        self.export_history_btn = QPushButton("导出历史")
        self.export_history_btn.clicked.connect(self.export_history)
        history_buttons_layout.addWidget(self.export_history_btn)
        
        history_layout.addLayout(history_buttons_layout)
        
    def set_history_data(self, history_data):
        """设置历史记录数据并更新表格"""
        self.history_data = history_data
        self.populate_history_table()
    
    def populate_history_table(self):
        """根据下载历史填充表格"""
        # 清空表格
        self.history_table.setRowCount(0)
        
        # 添加历史记录 (倒序显示，最新的在最上面)
        for i, item in enumerate(reversed(self.history_data)):
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            
            # 存储原始数据索引，以便右键菜单使用
            # 原始数据的索引是 len(data) - 1 - i
            original_index = len(self.history_data) - 1 - i
            
            # 添加播放图标
            play_btn = QPushButton("▶")
            play_btn.setMaximumWidth(30)
            play_btn.clicked.connect(lambda checked, idx=original_index: self.play_history_item_by_index(idx))
            self.history_table.setCellWidget(row, 0, play_btn)
            
            # 存储索引到 UserRole，供右键菜单使用
            title_item = QTableWidgetItem(item.get('title', '未知'))
            title_item.setData(Qt.ItemDataRole.UserRole, original_index)
            
            # 添加其他数据
            self.history_table.setItem(row, 1, title_item)
            self.history_table.setItem(row, 2, QTableWidgetItem(item.get('duration', '--:--')))
            self.history_table.setItem(row, 3, QTableWidgetItem(item.get('size', '未知')))
            self.history_table.setItem(row, 4, QTableWidgetItem(item.get('format', '未知')))
            self.history_table.setItem(row, 5, QTableWidgetItem(item.get('resolution', '未知')))
            self.history_table.setItem(row, 6, QTableWidgetItem(item.get('uploader', '未知')))
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.history_table.itemAt(position)
        if not item:
            return
            
        # 获取整行
        row = self.history_table.rowAt(position.y())
        # 获取存储在第一列（标题列）中的原始数据索引
        title_item = self.history_table.item(row, 1)
        if not title_item:
            return
            
        original_index = title_item.data(Qt.ItemDataRole.UserRole)
        if original_index is None or original_index >= len(self.history_data):
            return
            
        history_item = self.history_data[original_index]
        
        menu = QMenu()
        
        play_action = QAction("播放", self)
        play_action.triggered.connect(lambda: self.play_history_item(history_item))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        merge_action = QAction("合成字幕...", self)
        merge_action.triggered.connect(lambda: self.prepare_subtitle_merge(history_item))
        menu.addAction(merge_action)
        
        translate_action = QAction("AI 翻译字幕...", self)
        translate_action.triggered.connect(lambda: self.prepare_subtitle_translate(history_item))
        menu.addAction(translate_action)
        
        menu.exec(QCursor.pos())

    def prepare_subtitle_merge(self, item):
        """准备字幕合成"""
        video_path = item.get('filepath')
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "错误", "找不到视频文件")
            return
            
        # 尝试猜测字幕文件位置 (同名 .srt 或 .vtt)
        base_path = os.path.splitext(video_path)[0]
        default_sub = None
        for ext in ['.srt', '.vtt']:
            if os.path.exists(base_path + ext):
                default_sub = base_path + ext
                break
        
        dir_path = os.path.dirname(video_path)
        
        # 让用户选择字幕文件
        subtitle_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择字幕文件", 
            default_sub if default_sub else dir_path,
            "字幕文件 (*.srt *.vtt)"
        )
        
        if subtitle_path:
            self.request_merge_subtitle.emit(video_path, subtitle_path)

    def prepare_subtitle_translate(self, item):
        """准备字幕翻译"""
        video_path = item.get('filepath')
        # 尝试猜测字幕文件位置 (同名 .srt 或 .vtt)
        # 如果是视频文件，尝试找同名SRT
        # 如果下载的就是字幕文件（仅字幕模式），直接使用
        
        default_sub = None
        if video_path:
            if video_path.endswith(('.srt', '.vtt')):
                default_sub = video_path
            else:
                base_path = os.path.splitext(video_path)[0]
                for ext in ['.srt', '.vtt']:
                    # 尝试找 video.en.srt, video.srt 等
                    candidates = [
                        base_path + ext,
                        base_path + ".en" + ext,
                        base_path + ".ja" + ext
                    ]
                    for cand in candidates:
                        if os.path.exists(cand):
                            default_sub = cand
                            break
                    if default_sub:
                        break
        
        start_dir = os.path.dirname(video_path) if video_path else ""
        
        subtitle_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择要翻译的字幕文件", 
            default_sub if default_sub else start_dir,
            "字幕文件 (*.srt)" # 目前仅支持 SRT
        )
        
        if subtitle_path:
            self.request_translate_subtitle.emit(subtitle_path)

    def play_history_item_by_index(self, index):
        if 0 <= index < len(self.history_data):
            self.play_history_item(self.history_data[index])

    def play_history_item(self, item):
        """播放历史记录中的项目"""
        import subprocess
        
        file_path = item.get('filepath')
        if file_path and os.path.exists(file_path):
            # 使用系统默认应用打开文件
            try:
                if os.name == 'nt': # Windows
                    os.startfile(file_path)
                elif os.name == 'posix': # macOS or Linux
                    import sys
                    if sys.platform == 'darwin':
                        subprocess.Popen(['open', file_path])
                    else:
                        subprocess.Popen(['xdg-open', file_path])
            except Exception as e:
                QMessageBox.warning(self, "播放失败", f"无法播放文件: {str(e)}")
        else:
            QMessageBox.warning(self, "文件不存在", "找不到下载的文件，可能已被移动或删除。")
    
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(self, '确认', '确定要清空所有下载历史记录吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.request_clear_history.emit()
    
    def export_history(self):
        """导出历史记录到文件"""
        self.request_export_history.emit()
