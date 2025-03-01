#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
                            QMessageBox)
from PyQt6.QtCore import Qt
import os
from datetime import datetime

class HistoryTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.initUI()
        
    def initUI(self):
        # 历史记录标签页布局
        history_layout = QVBoxLayout(self)
        
        # 创建历史记录表格
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["", "标题", "时长", "大小", "格式", "分辨率", "来源"])
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 标题列自适应
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
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
        
        # 填充历史记录表格
        self.populate_history_table()
    
    def populate_history_table(self):
        """根据下载历史填充表格"""
        # 清空表格
        self.history_table.setRowCount(0)
        
        # 添加历史记录
        for item in self.main_window.download_history:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            
            # 添加播放图标
            play_btn = QPushButton("▶")
            play_btn.setMaximumWidth(30)
            play_btn.clicked.connect(lambda checked, item=item: self.play_history_item(item))
            self.history_table.setCellWidget(row, 0, play_btn)
            
            # 添加其他数据
            self.history_table.setItem(row, 1, QTableWidgetItem(item.get('title', '未知')))
            self.history_table.setItem(row, 2, QTableWidgetItem(item.get('duration', '--:--')))
            self.history_table.setItem(row, 3, QTableWidgetItem(item.get('size', '未知')))
            self.history_table.setItem(row, 4, QTableWidgetItem(item.get('format', '未知')))
            self.history_table.setItem(row, 5, QTableWidgetItem(item.get('resolution', '未知')))
            self.history_table.setItem(row, 6, QTableWidgetItem(item.get('uploader', '未知')))
    
    def play_history_item(self, item):
        """播放历史记录中的项目"""
        import subprocess
        
        file_path = item.get('filepath')
        if file_path and os.path.exists(file_path):
            # 使用系统默认应用打开文件
            try:
                subprocess.Popen(['open', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            self.main_window.download_history = []
            self.history_table.setRowCount(0)
            self.main_window.save_history()
            self.main_window.populate_example_data()
    
    def export_history(self):
        """导出历史记录到文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出历史记录", 
                                                  os.path.expanduser("~/Downloads/youtube_history.csv"),
                                                  "CSV文件 (*.csv)")
        if file_path:
            if self.main_window.history_manager.export_history_to_csv(file_path, self.main_window.download_history):
                QMessageBox.information(self, "导出成功", f"历史记录已导出到: {file_path}")
            else:
                QMessageBox.critical(self, "导出失败", "导出历史记录时出错")