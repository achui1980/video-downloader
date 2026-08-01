# 渐进式解耦重构设计

日期：2026-08-01
方案：渐进式解耦（Approach A）

## 背景与目标

`ui.py`（787 行）是上帝类，混入了 UI 构建、下载编排、字幕功能、历史、设置读取。线程模型混乱（`custom_events.py` 是死代码、`api_server.py` 存在忙轮询和掩盖问题的补丁）。存在真实 API Key 提交进仓库、重复 except、四处硬编码格式字符串等技术债。

重构目标：在不改变外部行为的前提下，把 `ui.py` 拆成职责清晰的模块，统一线程模型，清理技术债。**不引入新功能、不改变 API 路由/插件契约。**

## 目标结构

```
main.py                       # 不变
ui.py                         # 瘦身：窗口/侧边栏装配 + 页面注册 + 信号路由
pages/
  __init__.py
  new_download_page.py        # 原 init_new_download_page + analyze_url/update_video_info
  tasks_page.py               # 原 init_tasks_page + TaskWidget 容器增删
download_controller.py        # 下载编排：download_threads/active_tasks/进度/取消/完成
download_worker.py            # 纯 Python 下载 worker（threading.Thread + 回调 + done 事件）
constants.py                  # FORMAT_OPTIONS 等共享常量（格式选项唯一来源）
tabs/                         # 保持不变（HistoryTab / SettingsTab 只是 UI 表面）
```

## 第 1 节：拆分 ui.py

- 页面模块只暴露 `build_page() -> QWidget` + 信号，不碰其他页面。
- `ui.py` 不再直接持有线程和 TaskWidget；`DownloadController` 持有它们，通过 Qt 信号与页面通信。
- `history`/`settings` 页保持 `tabs/` 不变。

## 第 2 节：统一线程模型

- 删除 `custom_events.py` 及其在 `ui.py` 的 `self.customEvent` 绑定。
- 新增 `download_worker.py`：`threading.Thread` + 回调（`on_progress`/`on_complete`/`on_error`）+ `done` 事件 + `cancel()`。
- `download_thread.py` 的 `DownloadThread(QThread)` 变成 worker 的薄封装（GUI 侧保留信号）。
- `api_server.py` 改用 worker + `asyncio.to_thread` 等待，删除 `while thread.isRunning(): sleep(1)` 忙轮询和"手动置为 completed"补丁。
- `download_thread.py` 里 `cancel()` 对 yt-dlp 私有 API `_finish_multiline_status` 的依赖，换成 yt-dlp 官方 `progress_hooks` 取消钩子。

## 第 3 节：共享常量与清理

- 新增 `constants.py`：`FORMAT_OPTIONS`（8 种格式唯一来源）、字幕语言常量。
- `config.py` 与 `config.json` 的真实 API Key 替换为占位符。
- 删除空 `history.json`。
- 修 `ai_translator.py` 重复的 except；`download_manager.py` 裸 `except: pass` 改记日志。

## 第 4 节：设置模型

- `SettingsTab` 增加 `get_settings() -> DownloadSettings` 和 `apply_settings()`；`ui.py` 不再逐个读 `settings_tab.xxx.text()`。
- `DownloadOptions` dataclass（url、format、path、subtitle、proxy、limit、cookies）统一传给 controller。

## 不变量（重构不得违反）

- API 路由：`POST /api/v1/download`、`GET /api/v1/status/{task_id}`、`DELETE /api/v1/download/{task_id}` 不变。
- 插件契约：`chrome-plugin/popup.js`、`background.js`、`manifest.json` 不改（格式字符串由 constants.py 注释说明同步）。
- 历史文件：`~/youtube_downloader_history.json` 读写格式不变。
- 下载产物：文件名/输出目录逻辑不变。

## 验证

- 每次改动后 `python -m py_compile <touched .py files>`
- 最后 `python main.py` 冒烟（GUI 打开、分析、下载、取消）
- `python api_server.py` + curl 验证三个路由

## 明确不做（YAGNI）

- 不做 DuckDB 历史、启动自动开 API、批量删除、插件显示日志等新功能。
- 不做全套分层重写。
- 不引入测试框架。
