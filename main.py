#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication
from ui import YoutubeDownloader

def main():
    app = QApplication(sys.argv)
    window = YoutubeDownloader()
    window.show()
    sys.exit(app.exec())  # 在 PyQt6 中 exec_() 改为 exec()

if __name__ == "__main__":
    main()