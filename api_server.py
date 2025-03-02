#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from download_thread import DownloadThread
import asyncio
import os

app = FastAPI(title="YouTube Downloader API")

class DownloadRequest(BaseModel):
    url: str
    format: str = "最佳质量"
    output_dir: Optional[str] = None
    subtitle: bool = False
    proxy: Optional[str] = None
    speed_limit: Optional[str] = None

class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str
    file_path: Optional[str] = None

# 存储下载任务的字典
download_tasks = {}

@app.post("/api/v1/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest):
    try:
        # 生成任务ID
        task_id = f"task_{len(download_tasks) + 1}"
        
        # 准备下载选项
        ydl_opts = {
            'outtmpl': os.path.join(
                request.output_dir or os.path.expanduser("~/Movies/yt-dlp"),
                '%(title)s.%(ext)s'
            ),
        }
        
        # 设置格式
        if request.format == "最佳质量":
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif request.format == "仅音频 (MP3)":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            
        # 设置字幕
        if request.subtitle:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            
        # 设置代理
        if request.proxy:
            ydl_opts['proxy'] = request.proxy
            
        # 设置速度限制
        if request.speed_limit:
            ydl_opts['ratelimit'] = request.speed_limit
            
        # 创建下载任务
        download_tasks[task_id] = {
            'status': 'pending',
            'message': '等待下载',
            'file_path': None,
            'thread': None
        }
        
        # 启动下载线程
        asyncio.create_task(download_video(task_id, request.url, ydl_opts))
        
        return DownloadResponse(
            task_id=task_id,
            status='pending',
            message='下载任务已创建',
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/status/{task_id}", response_model=DownloadResponse)
async def get_status(task_id: str):
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    task = download_tasks[task_id]
    return DownloadResponse(
        task_id=task_id,
        status=task['status'],
        message=task['message'],
        file_path=task['file_path']
    )

@app.delete("/api/v1/download/{task_id}")
async def cancel_download(task_id: str):
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    task = download_tasks[task_id]
    if task['thread'] and task['status'] == 'downloading':
        task['thread'].cancel()
        task['status'] = 'cancelled'
        task['message'] = '下载已取消'
        
    return {"message": "下载已取消"}

async def download_video(task_id: str, url: str, options: dict):
    """异步下载视频"""
    task = download_tasks[task_id]
    task['status'] = 'downloading'
    task['message'] = '正在下载'
    
    def progress_callback(progress):
        if progress['status'] == 'downloading':
            downloaded = progress.get('downloaded_bytes', 0)
            total = progress.get('total_bytes', 0) or progress.get('total_bytes_estimate', 0)
            if total > 0:
                percent = int(downloaded * 100 / total)
                task['message'] = f'下载进度: {percent}%'
    
    def complete_callback(info):
        # 移除调试打印
        task['status'] = 'completed'
        task['message'] = '下载完成'
        
        # 详细记录下载信息
        if info and 'requested_downloads' in info and info['requested_downloads']:
            download_info = info['requested_downloads'][0]
            task['file_path'] = download_info.get('filepath')
            print(f"下载完成: {task['file_path']}")
        else:
            print("下载完成，但无法获取文件路径信息")
            print(f"Info对象内容: {info}")
    
    def error_callback(error):
        task['status'] = 'error'
        task['message'] = f'下载失败: {error}'
        print(f"下载错误: {error}")
    
    # 创建下载线程
    thread = DownloadThread(url, options)
    
    # 确保信号连接正确
    thread.progress_signal.connect(progress_callback)
    thread.complete_signal.connect(complete_callback)
    thread.error_signal.connect(error_callback)
    
    task['thread'] = thread
    thread.start()
    
    # 等待下载完成，移除调试打印，增加状态检查
    while thread.isRunning():
        # 每秒检查一次状态
        await asyncio.sleep(1)
        print(f"任务 {task_id} 状态: {task['status']}, 消息: {task['message']}")
    
    # 线程结束后再次检查状态
    print(f"线程已结束，最终状态: {task['status']}")
    
    # 如果线程结束但状态仍为downloading，可能是信号没有正确触发
    if task['status'] == 'downloading':
        print("警告: 线程已结束但状态未更新，手动设置为completed")
        task['status'] = 'completed'
        task['message'] = '下载可能已完成(自动检测)'

def start_api_server(host="127.0.0.1", port=8765):
    """启动API服务器"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_api_server()