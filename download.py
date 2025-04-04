#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yt_dlp
from utils import format_size, format_time, format_duration
import os
from datetime import datetime
from my_logger import MyLogger
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
    
    @staticmethod
    def configure_logging(download_path, url=None):
        """
        配置yt-dlp的日志选项
        
        Args:
            download_path: 下载目录路径
            url: 视频URL (可选)
            
        Returns:
            包含日志配置的选项字典
        """
        # 创建日志目录
        log_dir = os.path.join(download_path, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 使用时间戳创建唯一的日志文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_id = url.split('?v=')[-1].split('&')[0] if url and '?v=' in url else 'video'
        log_file = os.path.join(log_dir, f'yt-dlp_{video_id}_{timestamp}.log')
        custom_logger = MyLogger.get_instance(log_file)
        # 配置日志选项
        log_opts = {
            # 移除错误的YoutubeDLLogger引用
            'logger': custom_logger,
            'logtostderr': False,  # 不将日志输出到stderr
            'quiet': False,        # 不使用安静模式
            'verbose': True,       # 使用详细模式
            'writedescription': True,  # 写入视频描述
            'writeinfojson': False,     # 写入视频信息JSON
            'logfile': log_file
        }
        
        return log_opts
    
    @staticmethod
    def prepare_download_options(format_option, download_path, subtitle_options=None, 
                                limit=None, proxy=None, use_chrome_cookies=False, enable_logging=True, url=None):
        """准备下载选项"""
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        }
        
        # 添加日志配置
        if enable_logging:
            log_opts = YouTubeDownloader.configure_logging(download_path, url)
            ydl_opts.update(log_opts)
        
        # 格式选择
        if format_option == "最佳质量":
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "仅视频":
            ydl_opts['format'] = 'bestvideo/best'
        elif format_option == "仅音频 (MP3)":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_option == "仅字幕":
            # 跳过视频下载，只下载字幕
            ydl_opts['skip_download'] = True
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitlesformat'] = 'vtt'  # 先下载为 VTT 格式
            
            # 默认下载中文和英文字幕
            ydl_opts['subtitleslangs'] = ['zh-Hans']
            
            # 添加字幕处理器，确保转换为srt格式
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            
            # 使用更明确的后处理器配置
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
                'when': 'before_dl',  # 在下载前运行后处理器
            })
            
            # 确保后处理器运行
            # ydl_opts['force_generic_extractor'] = False
        elif format_option == "1080p":
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "720p":
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "480p":
            ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best[height<=480]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif format_option == "360p":
            ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best[height<=360]'
            ydl_opts['merge_output_format'] = 'mp4'
        
        # 字幕选项
        if subtitle_options and subtitle_options.get('enabled', False):
            # 启用字幕下载
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            
            # 设置字幕格式为srt
            ydl_opts['subtitlesformat'] = 'srt'
            
            # 设置语言
            if subtitle_options.get('language'):
                ydl_opts['subtitleslangs'] = [subtitle_options['language']]
            else:
                # 默认下载所有可用字幕
                ydl_opts['subtitleslangs'] = ['en']
            
            # 添加字幕处理器，确保转换为srt格式
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
            })
        
        # 速度限制选项
        if limit:
            ydl_opts['ratelimit'] = limit
        
        # 代理选项
        if proxy:
            ydl_opts['proxy'] = proxy
            
        # 添加Chrome浏览器Cookies选项
        if use_chrome_cookies:
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
            
        return ydl_opts
    
    @staticmethod
    def get_download_info_from_result(info, format_option):
        """
        从下载结果中提取有用信息
        
        Args:
            info: 下载完成的视频信息
            format_option: 使用的格式选项
            
        Returns:
            整理后的下载信息字典
        """
        # 基本信息
        result = {
            'title': info.get('title', '未知'),
            'url': info.get('webpage_url', info.get('url', '未知')),
            'format': format_option,
            'duration': format_duration(info.get('duration', 0)),
            'size': '未知',
            'resolution': '未知',
            'uploader': info.get('uploader', '未知')
        }
        
        # 从下载信息获取更多详细数据
        if info and 'requested_downloads' in info:
            # 从请求的下载列表中获取第一个文件
            download_info = info['requested_downloads'][0] if info['requested_downloads'] else None
            if download_info:
                if 'filepath' in download_info:
                    # 使用实际下载的文件路径
                    filepath = download_info['filepath']
                    # 从文件路径中提取文件名（不含扩展名）
                    result['title'] = os.path.splitext(os.path.basename(filepath))[0]
                    result['filepath'] = filepath
                
                # 获取文件大小
                if 'filesize' in download_info and download_info['filesize']:
                    result['size'] = format_size(download_info['filesize'])
                elif 'filesize_approx' in download_info and download_info['filesize_approx']:
                    result['size'] = format_size(download_info['filesize_approx'])
                
                # 获取分辨率
                if 'resolution' in download_info and download_info['resolution']:
                    result['resolution'] = download_info['resolution']
                elif 'height' in download_info and download_info['height']:
                    result['resolution'] = f"{download_info['height']}p"
                
        return result