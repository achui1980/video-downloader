#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication
from ui import YoutubeDownloader
from api_server import start_api_server
import argparse

def main():
    parser = argparse.ArgumentParser(description='YouTube 视频下载器')
    parser.add_argument('--api', action='store_true', help='启动API服务器')
    parser.add_argument('--host', default="127.0.0.1", help='API服务器主机地址')
    parser.add_argument('--port', type=int, default=8765, help='API服务器端口')
    
    args = parser.parse_args()
    
    if args.api:
        # 启动API服务器
        start_api_server(host=args.host, port=args.port)
    else:
        # 启动GUI应用
        app = QApplication(sys.argv)
        window = YoutubeDownloader()
        window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()