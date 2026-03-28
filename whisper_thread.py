import os
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal


class WhisperThread(QThread):
    progress_signal = pyqtSignal(str, int, int)  # 状态消息, 当前步骤, 总步骤
    finished_signal = pyqtSignal(bool, str)  # 成功/失败, 文件路径或错误信息

    def __init__(self, video_path, language=None, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.language = language  # None 表示自动检测
        self.temp_audio_path = None

    def run(self):
        try:
            # 检查视频文件
            if not os.path.exists(self.video_path):
                raise FileNotFoundError(f"Video file not found: {self.video_path}")

            # 检查 ffmpeg
            import subprocess

            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise RuntimeError(
                    "FFmpeg not found. Please install ffmpeg: brew install ffmpeg"
                )

            # 检查取消
            if self.isInterruptionRequested():
                self.finished_signal.emit(False, "已取消")
                return

            self.progress_signal.emit("正在加载 Whisper 模型...", 1, 4)

            # 导入服务（延迟导入避免启动慢）
            from whisper_service import WhisperService

            service = WhisperService()
            if not service.load_model("base"):
                raise RuntimeError("Failed to load Whisper model")

            # 检查取消
            if self.isInterruptionRequested():
                self.finished_signal.emit(False, "已取消")
                return

            self.progress_signal.emit("正在提取音频...", 2, 4)

            # 提取音频
            self.temp_audio_path = service.extract_audio(self.video_path)

            # 检查取消
            if self.isInterruptionRequested():
                self._cleanup()
                self.finished_signal.emit(False, "已取消")
                return

            self.progress_signal.emit("正在转写中...", 3, 4)

            # 转写（此步骤为阻塞调用，优雅取消需等待完成）
            result = service.transcribe(self.temp_audio_path, language=self.language)

            # 检查取消（转写完成后检查）
            if self.isInterruptionRequested():
                self._cleanup()
                self.finished_signal.emit(False, "已取消")
                return

            # 生成 SRT
            srt_content = service.to_srt(result)

            # 保存文件
            video_dir = os.path.dirname(self.video_path)
            video_name = os.path.splitext(os.path.basename(self.video_path))[0]
            srt_path = os.path.join(video_dir, f"{video_name}.srt")

            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            self.progress_signal.emit("完成!", 4, 4)
            self.finished_signal.emit(True, srt_path)

        except Exception as e:
            self.finished_signal.emit(False, str(e))

        finally:
            # 清理临时文件
            self._cleanup()

    def _cleanup(self):
        if self.temp_audio_path and os.path.exists(self.temp_audio_path):
            try:
                os.remove(self.temp_audio_path)
            except Exception as e:
                print(f"Warning: Failed to clean up temp audio: {e}")
            self.temp_audio_path = None

    def cancel(self):
        self.requestInterruption()
