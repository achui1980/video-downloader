# Whisper 本地字幕生成功能设计

## 概述

为 YouTube Downloader 添加 Whisper 本地语音转字幕功能。用户可通过右键菜单对已下载的视频生成 .srt 字幕文件，无需依赖云端 API。

## 背景

项目已有 AI 字幕翻译功能（调用云端 API），但缺少从视频提取语音生成字幕的能力。本功能使用 OpenAI Whisper 本地模型，无 API 费用，支持 macOS Apple Silicon 优化。

## 功能需求

### 触发方式
- 用户在历史记录中右键点击视频 → 选择"生成字幕"
- 弹出语言选择对话框
- 用户确认后后台生成字幕

### 语言选择
- 下拉框选项：自动检测、中文、英文、日文、韩文、德文、法文、西班牙文等
- 默认选项：自动检测
- 如果用户选择具体语言，Whisper 使用该语言作为提示，可提高准确率

### 输出
- 格式：SRT 字幕文件
- 位置：与源视频文件同目录
- 命名：`{视频文件名}.srt`

## 技术方案

### 技术栈
- **Whisper**: openai-whisper，本地模型，无需 API Key
- **FFmpeg**: 音频提取（macOS 可通过 `brew install ffmpeg` 安装）
- **PyQt6**: UI 已在使用

### 模型选择
- **模型**: base（推荐）
- **原因**: Mac CPU 友好，中文识别效果较好

### 新增文件

#### 1. whisper_service.py
```
职责：封装 Whisper 模型加载和转写逻辑

类：WhisperService
方法：
- load_model(model_name="base") → 加载模型
- transcribe(audio_path, language=None) → 执行转写
- to_srt(result) → 转换结果为 SRT 格式

依赖：whisper, torch
```

#### 2. whisper_thread.py
```
职责：QThread 后台线程，避免 UI 阻塞

类：WhisperThread(QThread)
信号：
- progress_signal(str, int, int) → 状态消息, 当前进度, 总进度
- finished_signal(bool, str) → 成功/失败, 文件路径或错误信息

方法：
- run() → 执行转写流程
- cancel() → 取消操作
```

#### 3. generate_subtitle_dialog.py
```
职责：语言选择对话框

类：GenerateSubtitleDialog(QDialog)
布局：
- 标签：选择字幕语言
- 下拉框：自动检测 / 中文 / 英文 / 日文 / ...
- 按钮：确认 / 取消

方法：
- get_selected_language() → 返回选择的语言或 None（自动）
```

### 修改文件

#### tabs/history_tab.py
- 右键菜单添加"生成字幕"选项
- 新增 `request_generate_subtitle(video_path)` 信号

#### ui.py
- 连接信号到处理函数
- 显示进度对话框
- 处理完成回调

### 处理流程

```
用户右键 → generate_subtitle_dialog → 
  ├─ 取消 → 退出
  └─ 确认语言 → 显示进度对话框 → whisper_thread.run()
       ├─ 步骤1: ffmpeg 提取音频 → temp_audio.mp3
       ├─ 步骤2: whisper.load_model("base")
       ├─ 步骤3: whisper.transcribe(temp_audio, language=lang)
       ├─ 步骤4: 保存为 .srt
       └─ 清理 temp 文件 → 完成
```

### 错误处理
- FFmpeg 未安装 → 提示安装
- 视频文件不存在 → 提示错误
- 模型加载失败 → 显示错误信息
- 转写失败 → 回滚清理，提示错误

### 依赖

requirements.txt 新增：
```
openai-whisper>=20231117
torch>=2.0.0  # whisper 依赖
```

macOS Apple Silicon 用户可能需要：
```
pip install torch torchvision torchaudio
```
配合 Homebrew 安装 FFmpeg：
```
brew install ffmpeg
```

## UI 交互

### 右键菜单
```
▶ 播放
──────────
合成字幕...
AI 翻译字幕...
生成字幕...    ← 新增
```

### 语言选择对话框
```
┌─────────────────────────────────┐
│        生成字幕                  │
│                                 │
│  选择语言: [自动检测        ▼]   │
│                                 │
│         [取消] [确认]           │
└─────────────────────────────────┘
```

### 进度对话框
```
正在生成字幕...
──────────────────────────────────
步骤 1/2: 提取音频...
进度: 50%
──────────
[取消]
```

## 测试场景

1. 新视频下载完成后，右键 → 生成字幕 → 成功生成 .srt
2. 视频文件被移动/删除 → 提示文件不存在
3. FFmpeg 未安装 → 提示安装指引
4. 转写过程中取消 → 清理临时文件，UI 恢复
5. 不同语言视频 → 自动检测正确语言生成字幕
6. 已有同名 .srt 文件 → 覆盖或提示（待定：直接覆盖）

## 待定项

1. 已有同名字幕文件时的处理策略
2. 批量生成（暂不在本版本实现）
