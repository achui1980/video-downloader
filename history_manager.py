#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime

class HistoryManager:
    def __init__(self, history_file=None):
        if history_file is None:
            # 默认保存在用户目录下
            self.history_file = os.path.expanduser("~/youtube_downloader_history.json")
        else:
            self.history_file = history_file
        
    def save_history(self, history_list):
        """保存下载历史到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_list, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存历史记录失败: {str(e)}")
            return False
    
    def load_history(self):
        """从文件加载下载历史"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载历史记录失败: {str(e)}")
            return []
    
    def add_history_item(self, title, url, format_option):
        """创建一个新的历史记录项"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 处理标题：去除路径和扩展名
        if title and isinstance(title, str):
            # 先去除路径
            title = os.path.basename(title)
            # 再去除扩展名
            title = os.path.splitext(title)[0]
        
        return {
            'title': title,
            'url': url,
            'format': format_option,
            'time': now
        }
    
    def export_history_to_csv(self, file_path, history_list):
        """导出历史记录到CSV文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("标题,URL,格式,下载时间\n")
                for item in history_list:
                    f.write(f"{item.get('title', '未知')},{item.get('url', '')},{item.get('format', '')},{item.get('time', '')}\n")
            return True
        except Exception as e:
            print(f"导出历史记录失败: {str(e)}")
            return False