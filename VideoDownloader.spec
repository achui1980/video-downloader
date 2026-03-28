# -*- mode: python ; coding: utf-8 -*-

import os
import shutil

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('assets/icon.png', 'assets'),
    ],
    hiddenimports=[
        'whisper',
        'openai',
        'openai.whisper',
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'yt_dlp',
        'yt_dlp.utils',
        'loguru',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'pygame',
        'cv2',
        'notebook',
        'jupyter',
        'IPython',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.png',
    plist={
        'CFBundleName': 'VideoDownloader',
        'CFBundleDisplayName': 'YouTube Video Downloader',
        'CFBundleIdentifier': 'com.yt-downloader.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleExecutable': 'VideoDownloader',
        'LSMinimumSystemVersion': '10.13',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'CFBundleIconFile': 'icon.png',
    },
)
