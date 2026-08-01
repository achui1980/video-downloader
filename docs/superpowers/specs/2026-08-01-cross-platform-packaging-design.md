# 跨平台打包设计（GitHub Actions）

日期：2026-08-01
状态：已确认

## 目标

用 GitHub Actions 把桌面 GUI 应用（PyQt6 + yt-dlp）自动打包为三平台安装包：

- Windows：Inno Setup 安装包
- macOS：arm64（Apple Silicon）与 x86_64（Intel）两个 .dmg
- Linux：AppImage

触发方式：push tag `v*`，产物上传到 GitHub Releases。

范围明确**不做**：

- 不打包 API 服务（`api_server.py` 保持源码/手动运行，仅供 chrome-plugin 使用）
- 不打包 Whisper（`openai-whisper` + torch 不进入产物，打包后该功能报错即可）
- 不在 CI 中做签名/公证

## 方案选型

采用 **PyInstaller 矩阵构建**（方案 A）：

- 复用现有 `VideoDownloader.spec`，各平台 job 并行运行 PyInstaller
- 对比过的备选：BeeWare Briefcase（需重构项目结构，否决）、Nuitka（CI 编译慢、PyQt6 兼容坑多，否决）

## 架构与组件

### 1. GitHub Actions Workflow：`.github/workflows/build.yml`

- **触发**：`push: tags: ['v*']`
- **矩阵** 4 个 job：

| Job | Runner | 产物 |
|-----|--------|------|
| windows | `windows-latest` | `VideoDownloader-<ver>-x64-setup.exe` |
| macos-arm64 | `macos-latest` | `VideoDownloader-<ver>-arm64.dmg` |
| macos-intel | `macos-13` | `VideoDownloader-<ver>-x86_64.dmg` |
| linux | `ubuntu-latest` | `VideoDownloader-<ver>-x86_64.AppImage` |

- **共用步骤**（每 job）：
  1. checkout、setup-python（3.12）
  2. `pip install -r requirements-build.txt` + pyinstaller
  3. 下载对应平台固定版本 FFmpeg 静态构建
  4. 设置 `APP_VERSION` 环境变量（从 tag 提取）
  5. `pyinstaller VideoDownloader.spec --noconfirm`
  6. 包壳为安装包（Inno Setup / hdiutil+create-dmg / AppImage 工具）
  7. `softprops/action-gh-release` 上传产物到 Releases

### 2. 依赖拆分

新增 `requirements-build.txt`（打包用，**排除** `openai-whisper`；`openai` 必须保留）：

```
PyQt6>=6.8.1
yt-dlp>=2026.3.17
requests>=2.28.0
openai>=1.0.0
loguru
```

注：`openai` 必须保留——`ui.py:39` 顶层导入 `translation_dialog` → `ai_translator` → `openai`，剔除会导致 app 启动崩溃。`openai` 为轻量 SDK，体积可接受。`requirements.txt` 保留不动，开发环境仍可用 Whisper。spec 中现有的 whisper/fastapi/uvicorn hiddenimports 建议移除（增大体积、无功能收益）。

### 3. FFmpeg 内置

- 各平台官方静态构建，固定版本 URL，CI 下载：
  - Windows：gyan.dev essentials 构建
  - macOS：evermeet.cx universal 构建
  - Linux：johnvansickle static 构建
- `VideoDownloader.spec` 按 `sys.platform` 分支，将 ffmpeg/ffprobe 加进 `binaries`
- `main.py` 启动时把 ffmpeg 所在目录注入 `os.environ['PATH']`（`_MEIPASS/ffmpeg/bin` 或 `_MEIPASS`），现有 shell 调用 `"ffmpeg"` 无需改代码

### 4. 资源路径修复（关键 bug）

当前 `config.py` 的 `get_config_path()` / `get_log_dir()` 基于 `__file__` 目录。macOS .app bundle 只读，打包后保存配置会失败。冻结态（`sys.frozen`）下重定向到用户数据目录：

- macOS：`~/Library/Application Support/VideoDownloader/`
- Windows：`%APPDATA%/VideoDownloader/`
- Linux：`~/.config/VideoDownloader/`

非冻结态保持现状（repo 内 config.json）。

### 5. 版本号

- tag 如 `v3.0.0` → `APP_VERSION=3.0.0`
- spec 通过 `os.environ.get('APP_VERSION', '1.0.0')` 设置 macOS plist 版本号与产物名
- 安装包文件名带版本号

### 6. Whisper 处理

- `whisper_thread.py` 已延迟导入 `whisper_service`，且 `run()` 整体 try/except 兜底
- 打包后点"生成字幕"会提示失败而非崩溃，可接受，不做额外 UI 隐藏

## 错误处理

- 每步 `set -e` / CI 步骤失败即 job 失败，不静默
- FFmpeg 下载失败：job 直接 fail，避免产出无 ffmpeg 的半成品
- 包壳失败：fail，不产生错误格式产物

## 测试与验证

- 无现有测试套件；验证方式为 CI 构建产物可启动
- 本地最低检查：`python -m py_compile` 被改动的 .py 文件
- 首次 CI 跑通后，人工在 Windows/macOS/Linux 各下载产物冒烟一次

## 代码改动清单

| 文件 | 改动 |
|------|------|
| `.github/workflows/build.yml` | 新增，完整 CI 流水线 |
| `VideoDownloader.spec` | 跨平台分支、ffmpeg binaries、APP_VERSION |
| `config.py` | 冻结态用户数据目录重定向 |
| `main.py` | 注入 ffmpeg 到 PATH |
| `requirements-build.txt` | 新增，无 whisper/openai |
| `build_macos.sh` / `build_windows.bat` | 保留，本地开发仍可用（不强制改） |

## 不做的事

- API 服务打包与分发（`api_server.py` 及 fastapi/uvicorn 不进入产物）
- Whisper 打包（`openai-whisper` + torch 不进入产物）
- 代码签名 / 公证 / notarization
- Windows/macOS 之外的安装包形态（deb、rpm 等）
