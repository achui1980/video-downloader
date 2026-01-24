import os

class Config:
    # 路径配置
    DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Movies/yt-dlp")
    DEFAULT_LOG_DIR_NAME = 'logs'
    
    # UI 默认值
    DEFAULT_VIDEO_URL = "https://www.youtube.com/shorts/RIrEOv7sXYo"
    APP_WINDOW_TITLE = 'YouTube 视频下载器'
    APP_WINDOW_SIZE = (900, 600)
    
    # API 配置
    API_HOST = "127.0.0.1"
    API_PORT = 8765
    
    # 下载配置
    DEFAULT_FORMAT = "最佳质量"
    DEFAULT_SYSTEM = "Mac OS"
    
    @staticmethod
    def get_log_dir(base_path=None):
        if base_path:
            return os.path.join(base_path, Config.DEFAULT_LOG_DIR_NAME)
        app_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(app_dir, Config.DEFAULT_LOG_DIR_NAME)

    @staticmethod
    def ensure_dirs(path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                print(f"Error creating directory {path}: {e}")
