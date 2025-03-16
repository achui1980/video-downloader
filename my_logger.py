from loguru import logger
import os
import sys
from datetime import datetime

class MyLogger:
    _instance = None
    @classmethod
    def get_instance(cls, log_file=None):
        """获取 MyLogger 的单例实例"""
        if cls._instance is None:
            cls._instance = cls(log_file)
        return cls._instance
    def __init__(self, log_file=None):
        # 移除默认的 sink
        logger.remove()
        
        # 添加控制台输出
        logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
        
        # 如果提供了日志文件，添加文件输出
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # 写入日志头信息
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"=== yt-dlp 下载日志 - 开始于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            
            # 添加文件日志
            logger.add(
                log_file, 
                level="DEBUG", 
                format="{time:HH:mm:ss} | {level: <8} | {message}",
                rotation="10 MB",  # 日志文件达到10MB时轮转
                retention="1 week"  # 保留1周的日志
            )
        
        self.logger = logger
    
    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            self.logger.debug(msg[8:])  # 去掉前缀
        else:
            self.info(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)
        
    # 兼容 yt-dlp 的接口
    def report_warning(self, msg):
        self.warning(msg)
        
    def report_error(self, msg):
        self.error(msg)