#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

class CustomLogger:
    """自定义的yt-dlp日志记录器"""
    
    def __init__(self, log_file=None):
        self.log_file = log_file
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 写入日志头信息
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"=== yt-dlp 下载日志 - 开始于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    def debug(self, msg):
        """记录调试信息"""
        if self.log_file:
            self._write_to_log('[DEBUG] ' + msg)
    
    def info(self, msg):
        """记录一般信息"""
        if self.log_file:
            self._write_to_log('[INFO] ' + msg)
    
    def warning(self, msg):
        """记录警告信息"""
        if self.log_file:
            self._write_to_log('[WARNING] ' + msg)
    
    def error(self, msg):
        """记录错误信息"""
        if self.log_file:
            self._write_to_log('[ERROR] ' + msg)
    
    def _write_to_log(self, msg):
        """写入日志文件"""
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')} {msg}\n")