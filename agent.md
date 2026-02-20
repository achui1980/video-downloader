# YouTube Downloader Project Analysis

## 1. Project Overview
This project is a comprehensive YouTube video downloader application built with Python and PyQt6. It features a modern desktop GUI, AI-powered subtitle translation, and integration with a Chrome browser extension via a local API server. The application uses `yt-dlp` as its core downloading engine.

## 2. Tech Stack

### Core
- **Language**: Python 3.12+
- **GUI Framework**: PyQt6 (with QSS styling)
- **Download Engine**: yt-dlp
- **Concurrency**: `QThread` for UI responsiveness, `asyncio` for API server

### API Server
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Protocol**: HTTP (REST API)

### AI Features
- **Client**: OpenAI SDK (Compatible with DeepSeek/ModelScope)
- **Function**: Subtitle translation (SRT format)

### Browser Extension
- **Platform**: Google Chrome (Manifest V3)
- **Tech**: JavaScript, HTML, CSS
- **Communication**: Fetch API to local FastAPI server

### Utilities
- **Logging**: Loguru
- **Config**: JSON based configuration

## 3. Project Structure

```
video-downloader/
├── main.py                 # Application entry point
├── ui.py                   # Main Window UI implementation
├── api_server.py           # FastAPI server for browser extension integration
├── ai_translator.py        # AI Subtitle translation logic
├── download_manager.py     # Centralized download configuration management
├── download_thread.py      # Background thread for download execution
├── history_manager.py      # JSON-based history persistence
├── subtitle_merger.py      # FFmpeg wrapper for merging subtitles
├── task_widget.py          # UI component for individual download tasks
├── tabs/                   # UI Tabs
│   ├── history_tab.py      # History view
│   └── settings_tab.py     # Settings view
├── chrome-plugin/          # Chrome Extension source
│   ├── manifest.json
│   ├── background.js       # Background service worker (Context menu logic)
│   └── popup.html/js       # Extension popup
├── .trae/documents/        # Design documents and future plans
└── requirements.txt        # Python dependencies
```

## 4. Key Features

### Desktop Application
- **Video Analysis**: Fetches metadata (title, duration, formats) from YouTube URLs.
- **Format Selection**: Supports various resolutions (1080p, 720p, etc.) and audio-only (MP3) extraction.
- **AI Translation**: 
  - Batched SRT translation using LLMs.
  - Streaming response support in UI.
  - "Reasoning content" handling (for DeepSeek R1/V3).
- **Subtitle Management**: 
  - Download original subtitles.
  - Merge subtitles into video files.
- **History**: Records download history with export (CSV) capability.
- **Settings**: Proxy support, Speed limits, Cookie import (Chrome).

### Browser Extension
- **Context Menu**: Right-click on links/pages to download directly.
- **Quick Actions**: One-click download for specific formats (Best, MP3, 1080p).
- **Feedback**: Visual feedback (badge text) for success/failure.

## 5. Architecture Data Flow

1.  **User Action**: 
    *   **Desktop**: User pastes URL -> `AnalyzeThread` -> `yt-dlp` -> UI Update.
    *   **Extension**: User clicks Context Menu -> `background.js` -> `POST /api/v1/download` -> `api_server.py`.
2.  **Download Execution**: 
    *   `DownloadManager` creates task -> `DownloadThread` starts -> `yt-dlp` downloads file.
    *   Progress signals sent to `TaskWidget` (Desktop) or polled by API (Extension).
3.  **Post-Processing**:
    *   FFmpeg merges video+audio+subtitles.
    *   `HistoryManager` saves record to `history.json`.

## 6. Future Roadmap (Inferred)
- **UI/UX Modernization**: Transitioning to a more web-style UI (Vue3 + FastAPI mentioned in docs).
- **Database**: Migration to DuckDB for history management.
- **Features**: 
  - Batch history deletion.
  - Enhanced browser plugin with download logs.
  - Context-aware subtitle translation optimization.
