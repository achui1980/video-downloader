#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import Config
from download_manager import DownloadManager
from download_worker import DownloadWorker

app = FastAPI(title="YouTube Downloader API")


class DownloadRequest(BaseModel):
    url: str
    format: str = Config.DEFAULT_FORMAT
    output_dir: Optional[str] = None
    subtitle: bool = False
    proxy: Optional[str] = None
    speed_limit: Optional[str] = None


class DownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str
    file_path: Optional[str] = None


manager = DownloadManager.get_instance()


@app.post("/api/v1/download", response_model=DownloadResponse)
async def start_download(request: DownloadRequest):
    try:
        subtitle_options = {"enabled": True} if request.subtitle else None

        ydl_opts = DownloadManager.prepare_download_options(
            format_option=request.format,
            download_path=request.output_dir or Config.DEFAULT_DOWNLOAD_PATH,
            subtitle_options=subtitle_options,
            limit=request.speed_limit,
            proxy=request.proxy,
            url=request.url,
        )

        task_id = manager.create_task(request.url, ydl_opts)
        task = manager.get_task(task_id)

        asyncio.create_task(_run_download(task_id, request.url, ydl_opts))

        return DownloadResponse(
            task_id=task_id,
            status=task["status"],
            message=task["message"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/status/{task_id}", response_model=DownloadResponse)
async def get_status(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return DownloadResponse(
        task_id=task_id,
        status=task["status"],
        message=task["message"],
        file_path=task.get("file_path"),
    )


@app.delete("/api/v1/download/{task_id}")
async def cancel_download(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    worker = task.get("worker")
    if worker and task["status"] in ("downloading", "pending"):
        worker.cancel()
        manager.update_task_status(task_id, "cancelled", "下载已取消")

    return {"message": "下载已取消"}


async def _run_download(task_id: str, url: str, options: dict):
    """异步下载：worker 在 to_thread 线程池运行，回调驱动状态更新，无忙轮询。"""
    task = manager.get_task(task_id)
    if not task:
        return

    manager.update_task_status(task_id, "downloading", "正在下载")

    def on_progress(progress):
        if progress["status"] == "downloading":
            downloaded = progress.get("downloaded_bytes", 0)
            total = progress.get("total_bytes", 0) or progress.get(
                "total_bytes_estimate", 0
            )
            if total > 0:
                percent = int(downloaded * 100 / total)
                manager.update_task_status(
                    task_id, "downloading", f"下载进度: {percent}%", percent
                )

    def on_complete(info):
        manager.update_task_status(task_id, "completed", "下载完成")
        if info and info.get("requested_downloads"):
            download_info = info["requested_downloads"][0]
            file_path = download_info.get("filepath")
            if file_path:
                task["file_path"] = file_path

    def on_error(message):
        if message == "cancelled":
            manager.update_task_status(task_id, "cancelled", "下载已取消")
        else:
            manager.update_task_status(task_id, "error", f"下载失败: {message}")

    worker = DownloadWorker(
        url,
        options,
        on_progress=on_progress,
        on_complete=on_complete,
        on_error=on_error,
    )
    task["worker"] = worker

    await asyncio.to_thread(worker.run)


def start_api_server(host=Config.API_HOST, port=Config.API_PORT):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()
