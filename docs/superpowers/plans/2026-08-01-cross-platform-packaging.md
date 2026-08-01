# 跨平台打包（GitHub Actions）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 GitHub Actions 把 PyQt6 桌面应用自动打包为 Windows（Inno Setup）、macOS（arm64 + x86_64 .dmg）、Linux（AppImage）三个平台的安装包，tag `v*` 推送时触发并上传到 GitHub Releases。

**Architecture:** 复用现有 `VideoDownloader.spec`（PyInstaller），workflow 用 OS 矩阵并行构建。每平台 CI 下载对应官方静态 FFmpeg 并注入 spec 的 `binaries`，`main.py` 启动时把 FFmpeg 目录加入 PATH。冻结态下 config/log 从只读 bundle 重定向到用户数据目录。版本号从 tag 注入产物名和 plist。

**Tech Stack:** PyInstaller、GitHub Actions、Inno Setup、hdiutil/create-dmg、AppImage-builder、FFmpeg 静态构建。

参考设计文档：`docs/superpowers/specs/2026-08-01-cross-platform-packaging-design.md`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `requirements-build.txt` | 打包依赖（无 openai-whisper） |
| `config.py` | 冻结态路径重定向（核心改动） |
| `main.py` | 冻结态注入 FFmpeg 到 PATH |
| `VideoDownloader.spec` | 跨平台 spec 重写（COLLECT + BUNDLE 标准结构） |
| `scripts/windows/installer.iss` | Inno Setup 脚本 |
| `scripts/linux/AppImageBuilder.yml` | AppImage 构建配方 |
| `.github/workflows/build.yml` | 完整 CI 流水线 |

**关键约束（AGENTS.md）**：无测试套件；Python 改动最低验证为 `python -m py_compile`；不做 API 服务产物、不做 Whisper、不做签名公证。

---

### Task 1: 创建 `requirements-build.txt`

**Files:**
- Create: `requirements-build.txt`

- [ ] **Step 1: 创建文件**

```
PyQt6>=6.8.1
yt-dlp>=2026.3.17
requests>=2.28.0
openai>=1.0.0
loguru
```

`openai` 必须保留——`ui.py:39` 顶层导入 `translation_dialog` → `ai_translator` → `openai`，剔除会启动崩溃。

- [ ] **Step 2: 验证**

Run: `python3 -m py_compile config.py`（确保环境无异常；依赖内容人工核对即可）
Expected: 无输出、exit 0

- [ ] **Step 3: Commit**

```bash
git add requirements-build.txt
git commit -m "build: 新增打包专用依赖文件 requirements-build.txt（排除 openai-whisper）"
```

---

### Task 2: `config.py` 冻结态路径重定向

**Files:**
- Modify: `config.py`（头部 import + `get_log_dir` / `get_config_path`）

- [ ] **Step 1: 修改 import 与新增私有方法**

在文件顶部 import 区（现有 `import os / json / constants`）追加 `import sys`，并在类外新增：

```python
def _app_data_dir():
    """返回用户数据目录。冻结态下 bundle 只读，需重定向到用户目录。"""
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            base = os.path.expanduser('~/Library/Application Support')
        elif sys.platform == 'win32':
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return os.path.join(base, 'VideoDownloader')
    return os.path.dirname(os.path.abspath(__file__))
```

- [ ] **Step 2: 修改 `get_log_dir`**

现有（`config.py:49-53`）：
```python
@staticmethod
def get_log_dir(base_path=None):
    if base_path:
        return os.path.join(base_path, Config.DEFAULT_LOG_DIR_NAME)
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, Config.DEFAULT_LOG_DIR_NAME)
```

改为：
```python
@staticmethod
def get_log_dir(base_path=None):
    if base_path:
        return os.path.join(base_path, Config.DEFAULT_LOG_DIR_NAME)
    return os.path.join(_app_data_dir(), Config.DEFAULT_LOG_DIR_NAME)
```

- [ ] **Step 3: 修改 `get_config_path`**

现有（`config.py:64-66`）：
```python
@staticmethod
def get_config_path():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, Config.CONFIG_FILE_NAME)
```

改为：
```python
@staticmethod
def get_config_path():
    return os.path.join(_app_data_dir(), Config.CONFIG_FILE_NAME)
```

- [ ] **Step 4: `save_config` 前确保目录存在**

现有（`config.py:82-89`）：
```python
@classmethod
def save_config(cls):
    config_path = cls.get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cls.settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
```

改为：
```python
@classmethod
def save_config(cls):
    config_path = cls.get_config_path()
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(cls.settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
```

- [ ] **Step 5: 验证**

Run: `python3 -m py_compile config.py`
Expected: 无输出、exit 0

再验证非冻结态行为不变：
Run: `python3 -c "import config; print(config.Config.get_config_path())"`
Expected: 打印 `.../video-downloader/config.json`（仓库内路径）

- [ ] **Step 6: Commit**

```bash
git add config.py
git commit -m "fix: 冻结态下 config/log 路径重定向到用户数据目录"
```

---

### Task 3: `main.py` 冻结态注入 FFmpeg 到 PATH

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 新增 `_setup_frozen_paths` 并在 `main()` 顶部调用**

现有 `main.py`：
```python
def main():
    """应用程序入口点"""
    app = QApplication(sys.argv)
```

改为：
```python
def _setup_frozen_paths():
    """冻结态下将随包分发的 ffmpeg/ffprobe 目录注入 PATH。"""
    if getattr(sys, 'frozen', False):
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        ffmpeg_dir = os.path.join(bundle_dir, 'ffmpeg')
        if os.path.isdir(ffmpeg_dir):
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')


def main():
    """应用程序入口点"""
    _setup_frozen_paths()
    app = QApplication(sys.argv)
```

- [ ] **Step 2: 验证**

Run: `python3 -m py_compile main.py`
Expected: 无输出、exit 0

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: 冻结态启动时将内置 ffmpeg 目录注入 PATH"
```

---

### Task 4: 重写 `VideoDownloader.spec` 为跨平台标准结构

**Files:**
- Modify: `VideoDownloader.spec`

- [ ] **Step 1: 整体重写 spec**

```python
# -*- mode: python ; coding: utf-8 -*-
import os
import sys

APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
FFMPEG_DIR = os.environ.get('FFMPEG_DIR', '')

datas = [
    ('README.md', '.'),
    ('assets/icon.png', 'assets'),
]

binaries = []
if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
    for name in ('ffmpeg', 'ffprobe'):
        exe_name = name + ('.exe' if sys.platform == 'win32' else '')
        path = os.path.join(FFMPEG_DIR, exe_name)
        if os.path.exists(path):
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
```

注意点：
- `exclude_binaries=True` 的 EXE + COLLECT 是标准 onedir 结构；macOS 用 BUNDLE 包 COLLECT 产出 .app。
- 原 spec 的 `whisper/fastapi/uvicorn` hiddenimports 已移除，excludes 显式剔除 `whisper/torch/fastapi/uvicorn`（打包后"生成字幕"报错但不崩溃）。
- `assets/icon.png` 是 PNG，Windows 下不传 icon（PyInstaller 需要 .ico，避免构建失败）；macOS 用 PNG 可直接用于 plist/图标。

- [ ] **Step 2: 验证 spec 语法可加载**

Run: `python3 -c "compile(open('VideoDownloader.spec').read(), 'VideoDownloader.spec', 'exec'); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add VideoDownloader.spec
git commit -m "build: 重写 spec 为跨平台结构，支持 ffmpeg 注入与版本号"
```

---

### Task 5: 新增 Windows Inno Setup 脚本

**Files:**
- Create: `scripts/windows/installer.iss`

- [ ] **Step 1: 创建目录与脚本**

```bash
mkdir -p scripts/windows
```

```iss
#define MyAppName "VideoDownloader"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppDir "..\..\dist\VideoDownloader"

[Setup]
AppId={{8F1B6D2A-9C42-4E6E-9F3D-2A1B0C7E5A90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=VideoDownloader
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\setup
OutputBaseFilename=VideoDownloader-{#MyAppVersion}-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#MyAppDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\VideoDownloader.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\VideoDownloader.exe"

[Run]
Filename: "{app}\VideoDownloader.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
```

- [ ] **Step 2: 验证**

Run: `python3 -c "print('iss content ok (Inno Setup only compiles on Windows)')"`
Expected: 打印提示。真实编译在 CI 的 windows job 进行，本地无需安装 Inno Setup。

- [ ] **Step 3: Commit**

```bash
git add scripts/windows/installer.iss
git commit -m "build: 新增 Windows Inno Setup 安装脚本"
```

---

### Task 6: 新增 Linux AppImage 构建配方

**Files:**
- Create: `scripts/linux/AppImageBuilder.yml`

- [ ] **Step 1: 创建目录与配方**

```bash
mkdir -p scripts/linux
```

```yaml
version: 1
AppDir:
  path: ../../dist/VideoDownloader
  app_info:
    id: com.yt-downloader.app
    name: VideoDownloader
    icon: video-downloader
    version: "{{version}}"
    exec: VideoDownloader
    exec_args: $@
  apt:
    arch: amd64
    allow_unauthenticated: true
    sources:
      - sourceline: "deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ jammy main universe"
    packages:
      - libglib2.0-0
      - libxcb-icccm4
      - libxcb-keysyms1
      - libxcb-image0
      - libxcb-randr0
      - libxcb-render-util0
      - libxcb-shape0
      - libxcb-xinerama0
      - libxcb-xkb1
      - libxkbcommon-x11-0
      - libdbus-1-3
      - libegl1
      - libgl1
      - libfontconfig1
      - libfreetype6
  files:
    exclude:
      - usr/share/man
      - usr/share/doc
  test:
    ubuntu:
      image: appimagecrafters/tests-env:stable
      command: ./AppRun
    archlinux:
      image: appimagecrafters/tests-env-archlinux:latest
      command: ./AppRun
AppImage:
  arch: x86_64
  update-information: none
```

- [ ] **Step 2: 验证**

Run: `python3 -c "import yaml; yaml.safe_load(open('scripts/linux/AppImageBuilder.yml')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/linux/AppImageBuilder.yml
git commit -m "build: 新增 Linux AppImage 构建配方"
```

---

### Task 7: 新增 GitHub Actions workflow

**Files:**
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: 创建目录与 workflow**

```bash
mkdir -p .github/workflows
```

```yaml
name: Build & Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: pip install -r requirements-build.txt pyinstaller
      - name: Download FFmpeg
        shell: pwsh
        run: |
          Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile ffmpeg.zip
          Expand-Archive ffmpeg.zip -DestinationPath ffmpeg-dl
          New-Item -ItemType Directory -Force -Path ffmpeg
          Copy-Item "ffmpeg-dl/ffmpeg-*/bin/ffmpeg.exe" ffmpeg/
          Copy-Item "ffmpeg-dl/ffmpeg-*/bin/ffprobe.exe" ffmpeg/
      - name: Build with PyInstaller
        run: pyinstaller VideoDownloader.spec --noconfirm
        env:
          APP_VERSION: ${{ github.ref_name }}
          FFMPEG_DIR: ffmpeg
      - name: Build installer
        shell: pwsh
        run: |
          choco install innosetup -y
          $ver = "${{ github.ref_name }}" -replace '^v',''
          ISCC.exe /DMyAppVersion=$ver "scripts\windows\installer.iss"
      - name: Upload release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/setup/VideoDownloader-*-x64-setup.exe

  macos-arm64:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: pip install -r requirements-build.txt pyinstaller
      - name: Download FFmpeg
        run: |
          curl -s "https://evermeet.cx/ffmpeg/info/ffmpeg/release" -o ffmpeg-info.json
          URL="$(python3 -c "import json;print(json.load(open('ffmpeg-info.json'))['download']['zip'])")"
          curl -L "$URL" -o ffmpeg.zip
          mkdir -p ffmpeg
          unzip -o ffmpeg.zip -d ffmpeg
      - name: Build with PyInstaller
        run: pyinstaller VideoDownloader.spec --noconfirm
        env:
          APP_VERSION: ${{ github.ref_name }}
          FFMPEG_DIR: ffmpeg
      - name: Build dmg
        run: |
          ver="${{ github.ref_name }}"
          hdiutil create -volname "VideoDownloader" -srcfolder dist/VideoDownloader.app -ov -format UDZO dist/VideoDownloader-${ver}-arm64.dmg
      - name: Upload release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/VideoDownloader-*-arm64.dmg

  macos-intel:
    runs-on: macos-13
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: pip install -r requirements-build.txt pyinstaller
      - name: Download FFmpeg
        run: |
          curl -s "https://evermeet.cx/ffmpeg/info/ffmpeg/release" -o ffmpeg-info.json
          URL="$(python3 -c "import json;print(json.load(open('ffmpeg-info.json'))['download']['zip'])")"
          curl -L "$URL" -o ffmpeg.zip
          mkdir -p ffmpeg
          unzip -o ffmpeg.zip -d ffmpeg
      - name: Build with PyInstaller
        run: pyinstaller VideoDownloader.spec --noconfirm
        env:
          APP_VERSION: ${{ github.ref_name }}
          FFMPEG_DIR: ffmpeg
      - name: Build dmg
        run: |
          ver="${{ github.ref_name }}"
          hdiutil create -volname "VideoDownloader" -srcfolder dist/VideoDownloader.app -ov -format UDZO dist/VideoDownloader-${ver}-x86_64.dmg
      - name: Upload release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/VideoDownloader-*-x86_64.dmg

  linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: pip install -r requirements-build.txt pyinstaller appimage-builder
      - name: Download FFmpeg
        run: |
          curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" -o ffmpeg.tar.xz
          mkdir -p ffmpeg
          tar -xJf ffmpeg.tar.xz --strip-components=1 -C ffmpeg
      - name: Build with PyInstaller
        run: pyinstaller VideoDownloader.spec --noconfirm
        env:
          APP_VERSION: ${{ github.ref_name }}
          FFMPEG_DIR: ffmpeg
      - name: Prepare AppDir
        run: |
          mkdir -p dist/VideoDownloader/usr/share/icons/hicolor/512x512/apps
          cp assets/icon.png dist/VideoDownloader/usr/share/icons/hicolor/512x512/apps/video-downloader.png
      - name: Build AppImage
        run: |
          export APPIMAGE_EXTRACT_AND_RUN=1
          appimage-builder --recipe scripts/linux/AppImageBuilder.yml
      - name: Upload release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/VideoDownloader-*.AppImage
```

注意点：
- `macos-14` = arm64、`macos-13` = x86_64，明确锁定架构。
- evermeet.cx 提供 universal 构建，`download.zip` 字段可直接用；若执行时非 universal，需按 `uname -m` 选择架构 URL（见 Task 8 验证备注）。
- `softprops/action-gh-release` 需要 repo 已有 Release；tag 推送时若没有 release 会自动创建。

- [ ] **Step 2: 验证 YAML 语法**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: 新增三平台打包流水线（tag v* 触发，产物上传 GitHub Releases）"
```

---

### Task 8: 本地冒烟与收尾

**Files:**
- Modify: 无（仅验证）

- [ ] **Step 1: 全部改动文件语法编译**

Run:
```bash
python3 -m py_compile config.py main.py
```
Expected: 无输出、exit 0

- [ ] **Step 2: 验证非冻结态 config 路径未受影响**

Run: `python3 -c "import config; print(config.Config.get_config_path())"`
Expected: 仓库内 `config.json` 路径（确认没破坏开发环境行为）

- [ ] **Step 3: 确认变更清单**

Run: `git status --short`
Expected: 恰好包含本计划创建/修改的 7 个文件（`requirements-build.txt`、`config.py`、`main.py`、`VideoDownloader.spec`、`scripts/windows/installer.iss`、`scripts/linux/AppImageBuilder.yml`、`.github/workflows/build.yml`）

- [ ] **Step 4: 提交计划文档并总结**

```bash
git add docs/superpowers/plans/2026-08-01-cross-platform-packaging.md
git commit -m "docs: 添加跨平台打包实施计划"
```

- [ ] **Step 5: 向用户说明验证方式与后续动作**

告知用户：
1. push 一个 `v*` tag 触发 CI（如 `git tag v3.0.0 && git push origin v3.0.0`）
2. 若 evermeet.cx macOS FFmpeg 非 universal，改 workflow 中两个 macos job 的下载逻辑为按 `uname -m` 选架构 URL
3. 首次跑通后人工在三个平台各冒烟一次产物

---

## 自检记录

- **Spec 覆盖**：设计文档中「架构与组件」的 1-6 全部有对应 Task（workflow / 依赖拆分 / FFmpeg / 路径修复 / 版本号 / Whisper）。
- **Placeholder**：无 TBD/TODO；所有文件给出完整内容。
- **类型一致性**：`APP_VERSION`、`FFMPEG_DIR` 环境变量在 spec 与 workflow 中命名一致；`_app_data_dir()` 在 config.py 中定义并被两个方法复用；Inno Setup 的 `MyAppVersion` / `MyAppDir` 与 workflow 传参一致。
