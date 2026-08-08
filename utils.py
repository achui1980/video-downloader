#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from constants import LANGUAGE_CODES

def get_app_version():
    """获取应用版本号。打包后读取内置 version.txt,开发模式读取 git 标签。"""
    if getattr(sys, "frozen", False):
        version_file = os.path.join(getattr(sys, "_MEIPASS", ""), "version.txt")
        if os.path.isfile(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                version = f.read().strip()
            if version:
                return version
        return "1.0.0"

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().lstrip("v")
    except (subprocess.SubprocessError, OSError):
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"dev-{result.stdout.strip()}"
    except (subprocess.SubprocessError, OSError):
        pass

    return "dev"

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

def get_language_code(language_name):
    """将语言名称转换为语言代码"""
    return LANGUAGE_CODES.get(language_name, None)
