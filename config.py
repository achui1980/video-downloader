import os
import json
import constants

class Config:
    # 路径配置
    DEFAULT_DOWNLOAD_PATH = os.path.expanduser("~/Movies/yt-dlp")
    DEFAULT_LOG_DIR_NAME = 'logs'
    CONFIG_FILE_NAME = 'config.json'
    
    # UI 默认值
    DEFAULT_VIDEO_URL = "https://www.youtube.com/shorts/RIrEOv7sXYo"
    APP_WINDOW_TITLE = 'YouTube 视频下载器'
    APP_WINDOW_SIZE = (900, 600)
    
    # API 配置
    API_HOST = "127.0.0.1"
    API_PORT = 8765
    
    # 下载配置
    DEFAULT_FORMAT = constants.DEFAULT_FORMAT
    DEFAULT_SYSTEM = "Mac OS"
    
    # 运行时配置存储
    settings = {
        "subtitle": {
            "enabled": False,
            "language": "自动",
            "only_langs": ["zh-Hans"] # 默认只选中中文
        },
        "ai_translator": {
            "api_key": "",
            "base_url": "https://api-inference.modelscope.cn/v1",
            "model": "deepseek-ai/DeepSeek-V3.2",
            "batch_size": "200"
        },
        "proxy": {
            "enabled": False,
            "url": ""
        },
        "other": {
            "limit_speed": False,
            "limit_rate": "",
            "chrome_cookies": False
        }
    }
    
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

    @staticmethod
    def get_config_path():
        app_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(app_dir, Config.CONFIG_FILE_NAME)

    @classmethod
    def load_config(cls):
        """从文件加载配置"""
        config_path = cls.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    # 递归合并配置，保留默认值中存在但文件中不存在的新字段
                    cls._merge_dict(cls.settings, saved_settings)
            except Exception as e:
                print(f"Error loading config: {e}")

    @classmethod
    def save_config(cls):
        """保存配置到文件"""
        config_path = cls.get_config_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(cls.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    @staticmethod
    def _merge_dict(base_dict, new_dict):
        """递归合并字典"""
        for key, value in new_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                Config._merge_dict(base_dict[key], value)
            else:
                base_dict[key] = value
