#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yt_dlp
from utils import format_size, format_time, format_duration

class YouTubeDownloader:
    """YouTube视频下载器核心类"""
    
    @staticmethod
    def extract_info(url, options=None, download=False):
        """
        提取视频信息或下载视频
        
        Args:
            url: YouTube视频URL
            options: yt-dlp选项字典
            download: 是否下载视频
            
        Returns:
            视频信息字典
        """
        try:
            with yt_dlp.YoutubeDL(options or {}) as ydl:
                info = ydl.extract_info(url, download=download)
                return info
        except Exception as e:
            raise Exception(f"处理视频时出错: {str(e)}")
    
    @staticmethod
    def get_video_formats(info):
        """
        从视频信息中提取可用格式
        
        Args:
            info: 视频信息字典
            
        Returns:
            格式列表
        """
        formats = []
        if 'formats' in info:
            for fmt in info['formats']:
                format_note = fmt.get('format_note', '')
                if format_note:
                    resolution = fmt.get('resolution', 'N/A')
                    ext = fmt.get('ext', 'N/A')
                    formats.append({
                        'format_note': format_note,
                        'resolution': resolution,
                        'ext': ext,
                        'format_id': fmt.get('format_id', '')
                    })
        return formats
    
    @staticmethod
    def get_video_summary(info):
        """
        获取视频摘要信息
        
        Args:
            info: 视频信息字典
            
        Returns:
            摘要信息字典
        """
        return {
            'title': info.get('title', '未知'),
            'uploader': info.get('uploader', '未知'),
            'duration': format_duration(info.get('duration', 0)),
            'upload_date': info.get('upload_date', '未知'),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'thumbnail': info.get('thumbnail', '')
        }