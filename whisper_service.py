import whisper
import os


class WhisperService:
    def __init__(self):
        self.model = None

    def load_model(self, model_name="base"):
        """加载 Whisper 模型"""
        self.model = whisper.load_model(model_name)
        return self.model is not None

    def transcribe(self, audio_path, language=None):
        """
        执行语音转写

        Args:
            audio_path: 音频文件路径
            language: 语言代码（None 表示自动检测）

        Returns:
            dict: Whisper 返回结果，包含 text, segments 等
        """
        if not self.model:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        options = {}
        if language:
            options["language"] = language

        result = self.model.transcribe(audio_path, **options)
        return result

    @staticmethod
    def to_srt(result):
        """
        将 Whisper 结果转换为 SRT 格式

        Args:
            result: Whisper transcribe 返回的结果

        Returns:
            str: SRT 格式字符串
        """
        segments = result.get("segments", [])
        srt_lines = []

        for i, segment in enumerate(segments, start=1):
            start = WhisperService._format_timestamp(segment["start"])
            end = WhisperService._format_timestamp(segment["end"])
            text = segment["text"].strip()

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")

        return "\n".join(srt_lines)

    @staticmethod
    def _format_timestamp(seconds):
        """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def extract_audio(video_path, output_path=None):
        """
        使用 ffmpeg 从视频提取音频

        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径（None 则生成临时文件）

        Returns:
            str: 音频文件路径
        """
        import subprocess

        if output_path is None:
            import tempfile

            output_path = os.path.join(tempfile.gettempdir(), "whisper_audio_temp.mp3")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vn",  # 禁用视频
            "-acodec",
            "mp3",
            "-y",  # 覆盖已存在的文件
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_path
