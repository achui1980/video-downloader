from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt
from ai_translator import TranslationThread

class TranslationDialog(QDialog):
    def __init__(self, parent, api_key, base_url, model, input_path, batch_size=200):
        super().__init__(parent)
        self.setWindowTitle("AI 字幕翻译中...")
        self.resize(800, 600)
        
        self.layout = QVBoxLayout(self)
        
        # 状态标签
        self.status_label = QLabel("准备开始翻译...")
        self.layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)
        
        # 实时预览区域 (现在直接显示流式文本)
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #cccccc; 
            font-family: Consolas, monospace;
            font-size: 13px;
        """)
        self.layout.addWidget(self.preview_area)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_translation)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(btn_layout)
        
        # 启动线程
        self.thread = TranslationThread(api_key, base_url, model, input_path, batch_size)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.stream_content_signal.connect(self.append_stream_content)
        self.thread.finished_signal.connect(self.translation_finished)
        self.thread.start()
        
    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"正在翻译: {current}/{total} 行 (按批次)")
        
    def append_stream_content(self, text_chunk, is_reasoning):
        # 移动光标到末尾
        cursor = self.preview_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        if is_reasoning:
            # 思考内容使用灰色斜体显示
            char_fmt = cursor.charFormat()
            original_color = char_fmt.foreground().color()
            char_fmt.setForeground(Qt.GlobalColor.gray)
            char_fmt.setFontItalic(True)
            cursor.setCharFormat(char_fmt)
            cursor.insertText(text_chunk)
            
            # 恢复正常样式
            char_fmt.setForeground(original_color) # 这里可能需要显式设回原来的颜色，或者简单地重置
            char_fmt.setFontItalic(False)
            # cursor.setCharFormat(char_fmt) # 这行可能不立即生效，下一行重置
        else:
            # 正常内容使用默认样式 (亮色)
            char_fmt = cursor.charFormat()
            char_fmt.setForeground(Qt.GlobalColor.lightGray) # 或 #cccccc
            char_fmt.setFontItalic(False)
            cursor.setCharFormat(char_fmt)
            cursor.insertText(text_chunk)
            
        self.preview_area.setTextCursor(cursor)
        
        # 自动滚动到底部
        scrollbar = self.preview_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def cancel_translation(self):
        if self.thread.isRunning():
            self.thread.cancel()
            self.status_label.setText("正在取消...")
            self.cancel_btn.setEnabled(False)
            
    def translation_finished(self, success, message):
        if success:
            self.status_label.setText("翻译完成！")
            self.progress_bar.setValue(self.progress_bar.maximum())
            QMessageBox.information(self, "成功", f"字幕已保存至:\n{message}")
            self.accept()
        else:
            if "cancelled" in message:
                self.reject()
            else:
                QMessageBox.critical(self, "错误", f"翻译失败: {message}")
                self.reject()
