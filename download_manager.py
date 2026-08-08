import os
import uuid
import asyncio
import yt_dlp
from datetime import datetime
from config import Config
from my_logger import MyLogger
from utils import format_duration, format_size

class DownloadManager:
    _instance = None
    
    def __init__(self):
        self.tasks = {}
        self.logger = MyLogger.get_instance(Config.get_log_dir())
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_task(self, url, options=None):
        """创建新的下载任务"""
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            'id': task_id,
            'url': url,
            'status': 'pending',
            'progress': 0,
            'message': '等待开始',
            'created_at': datetime.now(),
            'options': options or {},
            'file_path': None,
            'thread': None  # 这里可能需要根据运行环境存储 Thread 或 asyncio Task
        }
        return task_id

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def update_task_status(self, task_id, status, message=None, progress=None):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task['status'] = status
            if message:
                task['message'] = message
            if progress is not None:
                task['progress'] = progress

    @staticmethod
    def prepare_download_options(format_option, download_path, subtitle_options=None, 
                                limit=None, proxy=None, use_chrome_cookies=False, enable_logging=True, url=None):
        """准备下载选项 - 迁移自 download.py"""
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
        }
        
        # 日志配置
        if enable_logging:
            log_dir = os.path.join(download_path, 'logs')
            if not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except OSError as e:
                    print(f"创建日志目录失败 {log_dir}: {e}")
            
            # 简单的日志文件名生成
            video_id = 'unknown'
            if url:
                if '?v=' in url:
                    video_id = url.split('?v=')[-1].split('&')[0]
                else:
                    video_id = url.split('/')[-1]
                    
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(log_dir, f'yt-dlp_{video_id}_{timestamp}.log')
            
            logger_instance = MyLogger.get_instance(log_file)
            ydl_opts.update({
                'logger': logger_instance,
                'logtostderr': False,
                'quiet': False,
                'verbose': True,
                'writedescription': True,
                'writeinfojson': False,
            })
        
        # 格式选择逻辑
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
            ydl_opts['skip_download'] = True
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitlesformat'] = 'vtt'
            
            if subtitle_options and 'languages' in subtitle_options:
                ydl_opts['subtitleslangs'] = subtitle_options['languages']
            else:
                ydl_opts['subtitleslangs'] = ['zh-Hans']
            
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
                'when': 'before_dl',
            })
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
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            
            # 使用 vtt 格式，然后转换为 srt
            ydl_opts['subtitlesformat'] = 'vtt'
            
            # 指定字幕语言
            if 'languages' in subtitle_options:
                # 传入的是语言列表
                ydl_opts['subtitleslangs'] = subtitle_options['languages']
            elif subtitle_options.get('language'):
                # 传入的是单个语言代码
                ydl_opts['subtitleslangs'] = [subtitle_options['language']]
            else:
                # 默认英文
                ydl_opts['subtitleslangs'] = ['en']
            
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            
            # 添加字幕转换后处理
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
                'when': 'before_dl', # 在下载前转换（如果可能）或者在合并前
            })
            
            # 确保视频中嵌入字幕
            ydl_opts['embedsubtitles'] = True
            
            # 使用 Chrome Cookies 下载字幕
            if use_chrome_cookies:
                ydl_opts['cookiesfrombrowser'] = ('chrome',)
            
        # 速度限制
        if limit:
            ydl_opts['ratelimit'] = limit
            
        # 代理
        if proxy:
            ydl_opts['proxy'] = proxy
            
        # Chrome Cookies
        if use_chrome_cookies:
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
            
        return ydl_opts

    @staticmethod
    def extract_info(url, options=None, download=False):
        try:
            with yt_dlp.YoutubeDL(options or {}) as ydl:
                return ydl.extract_info(url, download=download)
        except yt_dlp.utils.DownloadError as e:
            # 区分不同类型的错误
            error_msg = str(e)
            if "Private video" in error_msg:
                raise Exception("无法下载：这是一个私有视频")
            elif "Sign in" in error_msg:
                raise Exception("无法下载：需要登录才能观看")
            else:
                raise Exception(f"下载错误: {error_msg}")
        except Exception as e:
            raise Exception(f"处理视频时出错: {str(e)}")

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
                else:
                    # 合并下载时首个条目可能缺失高度，取所有条目的最大高度
                    heights = [
                        d.get('height', 0)
                        for d in info['requested_downloads']
                        if isinstance(d, dict) and d.get('height')
                    ]
                    if heights:
                        result['resolution'] = f"{max(heights)}p"
                    elif download_info.get('format_id'):
                        fmt = download_info.get('format_id', '')
                        for part in fmt.replace('+', ' ').split():
                            if part.isdigit() and int(part) > 100:
                                result['resolution'] = f"{int(part)}p"
                                break
        
        return result

    @staticmethod
    def get_video_summary(info):
        """获取视频摘要信息"""
        return {
            'title': info.get('title', '未知'),
            'uploader': info.get('uploader', '未知'),
            'duration': format_duration(info.get('duration', 0)),
            'upload_date': info.get('upload_date', '未知'),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'thumbnail': info.get('thumbnail', '')
        }
