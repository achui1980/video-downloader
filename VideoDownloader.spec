# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import tempfile

APP_VERSION = os.environ.get('APP_VERSION', '1.0.0').lstrip('v')
FFMPEG_DIR = os.environ.get('FFMPEG_DIR', '')

version_file = os.path.join(tempfile.gettempdir(), 'video-downloader-version.txt')
with open(version_file, 'w', encoding='utf-8') as f:
    f.write(APP_VERSION)

datas = [
    ('README.md', '.'),
    ('assets/icon.png', 'assets'),
    (version_file, '.'),
]

binaries = []
if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
    for name in ('ffmpeg', 'ffprobe'):
        exe_name = name + ('.exe' if sys.platform == 'win32' else '')
        path = os.path.join(FFMPEG_DIR, exe_name)
        if os.path.isfile(path):
            binaries.append((path, 'ffmpeg'))

icon_file = None
if sys.platform == 'darwin':
    icon_file = 'assets/icon.png'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'yt_dlp',
        'yt_dlp.utils',
        'loguru',
        'requests',
        'openai',
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
        'whisper',
        'torch',
        'fastapi',
        'uvicorn',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='VideoDownloader',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='VideoDownloader.app',
        icon='assets/icon.png',
        bundle_identifier='com.yt-downloader.app',
        info_plist={
            'CFBundleName': 'VideoDownloader',
            'CFBundleDisplayName': 'YouTube Video Downloader',
            'CFBundleIdentifier': 'com.yt-downloader.app',
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundlePackageType': 'APPL',
            'CFBundleExecutable': 'VideoDownloader',
            'LSMinimumSystemVersion': '10.13',
            'NSHighResolutionCapable': True,
            'NSPrincipalClass': 'NSApplication',
            'CFBundleIconFile': 'icon.png',
        },
    )
