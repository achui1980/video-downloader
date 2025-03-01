#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def format_duration(seconds):
    """格式化视频时长"""
    if not seconds:
        return "未知"
    
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    else:
        return f"{m}:{s:02d}"

def format_size(bytes):
    """格式化文件大小"""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024):.1f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.1f} GB"

def format_time(seconds):
    """将秒数格式化为时分秒格式，精确到秒"""
    # 确保输入是整数
    seconds = int(seconds)
    
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}分{s}秒"
    else:
        h, remainder = divmod(seconds, 3600)
        m, s = divmod(remainder, 60)
        return f"{h}时{m}分{s}秒"