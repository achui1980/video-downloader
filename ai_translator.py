import os
import re
from openai import OpenAI
from PyQt6.QtCore import QThread, pyqtSignal

class AITranslator:
    def __init__(self, api_key, base_url, model):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = model

    def translate_batch_stream(self, srt_content, target_lang="Chinese"):
        """
        使用 AI 批量翻译 SRT 文本 (流式)
        yields: (text_chunk, is_reasoning)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': f'You are a professional subtitle translator. Translate the subtitle text into {target_lang}. \n'
                                   f'IMPORTANT: Output strict SRT format only. Maintain exact timestamps and indexes. Do not merge lines.'
                    },
                    {
                        'role': 'user',
                        'content': srt_content
                    }
                ],
                stream=True,
                max_tokens=20480, # 增加输出 token 限制，防止长字幕被截断
                extra_body={"enable_thinking": True} # 适配 DeepSeek R1/V3
            )
            
            for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    
                    # 处理思考过程 (Reasoning Content)
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        yield (delta.reasoning_content, True)
                    
                    content = delta.content
                    if content:
                        yield (content, False)
                        
        except Exception as e:
            print(f"Translation error: {e}")
            raise e

class SubtitleParser:
    @staticmethod
    def parse_srt(file_path):
        """解析 SRT 文件，返回 (index, time_str, content) 列表"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
        matches = pattern.findall(content)
        
        subtitles = []
        for m in matches:
            subtitles.append({
                'index': m[0],
                'time': m[1],
                'content': m[2].strip()
            })
        return subtitles

    @staticmethod
    def build_srt_string(subtitles):
        """将字幕列表构建为 SRT 格式字符串"""
        output = []
        for sub in subtitles:
            output.append(f"{sub['index']}")
            output.append(f"{sub['time']}")
            output.append(f"{sub['content']}\n")
        return "\n".join(output)

class TranslationThread(QThread):
    progress_signal = pyqtSignal(int, int) # current_lines, total_lines
    stream_content_signal = pyqtSignal(str, bool) # chunk of translated text, is_reasoning
    finished_signal = pyqtSignal(bool, str) # success, message/path
    
    def __init__(self, api_key, base_url, model, input_path, batch_size=200):
        super().__init__()
        self.translator = AITranslator(api_key, base_url, model)
        self.input_path = input_path
        self.batch_size = batch_size
        self.is_cancelled = False

    def run(self):
        try:
            if not os.path.exists(self.input_path):
                raise Exception("Input file not found")

            # 1. 解析字幕
            subtitles = SubtitleParser.parse_srt(self.input_path)
            total_lines = len(subtitles)
            
            if total_lines == 0:
                raise Exception("No subtitles found in file")

            # 2. 分批处理
            final_translated_content = ""
            processed_lines = 0
            
            for i in range(0, total_lines, self.batch_size):
                if self.is_cancelled:
                    break
                
                batch_subs = subtitles[i : i + self.batch_size]
                batch_srt_content = SubtitleParser.build_srt_string(batch_subs)
                
                # 流式调用 AI
                try:
                    for chunk, is_reasoning in self.translator.translate_batch_stream(batch_srt_content):
                        if self.is_cancelled:
                            break
                        
                        # 发送给 UI 显示 (包括推理内容)
                        self.stream_content_signal.emit(chunk, is_reasoning)
                        
                        # 仅将非推理内容拼接到最终结果中
                        if not is_reasoning:
                            final_translated_content += chunk
                            
                except Exception as e:
                    self.stream_content_signal.emit(f"\n[Error in batch: {str(e)}]\n", False)
                
                processed_lines += len(batch_subs)
                self.progress_signal.emit(processed_lines, total_lines)

            # 3. 保存文件 (直接保存 AI 返回的完整内容)
            if not self.is_cancelled:
                # 构造输出文件名: video_zh.srt
                dir_name = os.path.dirname(self.input_path)
                base_name = os.path.splitext(os.path.basename(self.input_path))[0]
                if base_name.endswith('.en'):
                    output_name = base_name[:-3] + '_zh.srt'
                else:
                    output_name = base_name + '_zh.srt'
                
                output_path = os.path.join(dir_name, output_name)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(final_translated_content)
                
                self.finished_signal.emit(True, output_path)
            else:
                self.finished_signal.emit(False, "Translation cancelled")

        except Exception as e:
            self.finished_signal.emit(False, str(e))

    def cancel(self):
        self.is_cancelled = True
