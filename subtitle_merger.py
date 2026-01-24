import os
import sys
import platform
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

class SubtitleMergeThread(QThread):
    progress_signal = pyqtSignal(str) # 发送状态消息
    finished_signal = pyqtSignal(bool, str) # 成功/失败, 消息
    
    def __init__(self, video_path, subtitle_path, ffmpeg_path="ffmpeg"):
        super().__init__()
        self.video_path = video_path
        self.subtitle_path = subtitle_path
        self.ffmpeg_path = ffmpeg_path
        self.is_cancelled = False
        self.process = None

    def run(self):
        try:
            if not os.path.exists(self.video_path):
                raise Exception(f"视频文件不存在: {self.video_path}")
            if not os.path.exists(self.subtitle_path):
                raise Exception(f"字幕文件不存在: {self.subtitle_path}")

            # 1. 确定输出文件名
            # 规则: 原文件名_out.扩展名
            dir_name = os.path.dirname(self.video_path)
            base_name = os.path.basename(self.video_path)
            name_without_ext, ext = os.path.splitext(base_name)
            output_path = os.path.join(dir_name, f"{name_without_ext}_out{ext}")
            
            self.progress_signal.emit(f"准备合成: {base_name}")
            self.progress_signal.emit(f"输出路径: {output_path}")

            # 2. 确定字体
            system = platform.system()
            font_name = "Hiragino Sans GB" # macOS 默认
            if system == "Windows":
                font_name = "Microsoft YaHei"
            elif system == "Linux":
                font_name = "WenQuanYi Micro Hei" # 常见的 Linux 中文字体
            
            # 3. 构建 FFmpeg 命令
            # 注意: Windows 下 subtitles 滤镜的路径转义非常麻烦
            # 最稳妥的方法是将路径转换为相对路径，或者使用正斜杠并转义冒号
            
            # 使用相对路径策略以避免复杂的转义问题
            # 切换工作目录到视频所在目录
            working_dir = dir_name
            rel_video = os.path.basename(self.video_path)
            rel_sub = os.path.basename(self.subtitle_path)
            rel_out = os.path.basename(output_path)
            
            # 如果字幕文件不在同一目录，需要复制过去或者处理路径
            # 这里为了简单，我们假设我们能处理绝对路径的转义
            # FFmpeg 路径转义规则: 
            # Windows: C:\path\to\sub.srt -> C\\:/path/to/sub.srt
            # 并需要对反斜杠进行转义
            
            sub_path_arg = self.subtitle_path.replace('\\', '/').replace(':', '\\:')
            
            vf_arg = (
                f"subtitles='{sub_path_arg}':force_style='"
                f"FontName={font_name},FontSize=16,PrimaryColour=&H0000D7FF,"
                f"Outline=3,Shadow=0,Bold=1,MarginV=20'"
            )
            
            cmd = [
                self.ffmpeg_path,
                '-y', # 覆盖输出文件
                '-i', self.video_path,
                '-vf', vf_arg,
                '-c:a', 'copy',
                output_path
            ]
            
            # 打印调试命令
            # print(" ".join(cmd))
            
            # 4. 执行命令
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace' # 忽略编码错误
            )
            
            # 读取输出以更新进度 (FFmpeg 输出在 stderr)
            while True:
                if self.is_cancelled:
                    self.process.terminate()
                    break
                    
                line = self.process.stderr.readline()
                if not line and self.process.poll() is not None:
                    break
                
                if line:
                    # 简单的进度解析 (实际解析时间戳比较复杂，这里只做存活检测)
                    if "frame=" in line:
                        self.progress_signal.emit(f"正在合成: {line.strip()}")
            
            if self.process.returncode == 0:
                self.finished_signal.emit(True, f"合成成功: {os.path.basename(output_path)}")
            else:
                self.finished_signal.emit(False, "合成失败，请检查日志或 FFmpeg 配置")

        except Exception as e:
            self.finished_signal.emit(False, str(e))

    def cancel(self):
        self.is_cancelled = True
