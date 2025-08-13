import sys
import os
import binascii
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QPlainTextEdit, QTabWidget, QMessageBox, QSizePolicy,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QRectF, QMimeData, QThread, pyqtSignal, QObject
from PyQt5.QtGui import (
    QFont, QPainter, QLinearGradient, QColor, QPainterPath,
    QIcon, QClipboard, QDragEnterEvent, QDropEvent, QTextCursor
)

# 二进制转换工作线程
class ConversionWorker(QObject):
    completed = pyqtSignal(dict)  # 转换完成信号
    
    def __init__(self, file_data):
        super().__init__()
        self.file_data = file_data
    
    def run(self):
        """异步执行转换任务"""
        results = {}
        
        # C/C++转换
        results["C/C++"] = self.convert_to_cpp(self.file_data)
        
        # Go字节数组
        results["Go 字节数组"] = self.convert_to_go_bytes(self.file_data)
        
        # Go字符串
        results["Go 字符串"] = self.convert_to_go_string(self.file_data)
        
        # Python
        results["Python"] = self.convert_to_python(self.file_data)
        
        # Rust
        results["Rust"] = self.convert_to_rust(self.file_data)
        
        # 完成信号
        self.completed.emit(results)
    
    @staticmethod
    def convert_to_cpp(data):
        hex_data = binascii.hexlify(data).decode('ascii')
        hex_pairs = [f"0x{hex_data[i:i+2]}" for i in range(0, len(hex_data), 2)]
        return "unsigned char payload[] = {\n    " + ",\n    ".join(
            [", ".join(hex_pairs[i:i+16]) for i in range(0, len(hex_pairs), 16)]
        ) + "\n};\n\nsize_t payload_size = sizeof(payload);"

    @staticmethod
    def convert_to_go_bytes(data):
        hex_data = binascii.hexlify(data).decode('ascii')
        hex_pairs = [f"0x{hex_data[i:i+2]}" for i in range(0, len(hex_data), 2)]
        return "var payload = []byte{\n    " + ",\n    ".join(
            [", ".join(hex_pairs[i:i+16]) for i in range(0, len(hex_pairs), 16)]
        ) + "\n}"

    @staticmethod
    def convert_to_go_string(data):
        hex_str = binascii.hexlify(data).decode('ascii')
        escaped = ''.join([f"\\x{hex_str[i:i+2]}" for i in range(0, len(hex_str), 2)])
        return f'const payload = "{escaped}"'

    @staticmethod
    def convert_to_python(data):
        hex_str = binascii.hexlify(data).decode('ascii')
        return f'payload = bytes.fromhex("{hex_str}")'

    @staticmethod
    def convert_to_rust(data):
        hex_data = binascii.hexlify(data).decode('ascii')
        hex_pairs = [f"0x{hex_data[i:i+2]}" for i in range(0, len(hex_data), 2)]
        return "let payload: &[u8] = &[\n    " + ",\n    ".join(
            [", ".join(hex_pairs[i:i+16]) for i in range(0, len(hex_pairs), 16)]
        ) + "\n];"

# 按钮组件
class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(200, 50)
        self.setCursor(Qt.PointingHandCursor)
        font = QFont("Microsoft YaHei UI", 10)
        self.setFont(font)
        self.setStyleSheet("""
            QPushButton {
                background-color: #6E3DFF;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5D30E0;
            }
            QPushButton:pressed {
                background-color: #4C25C2;
            }
        """)

# 重构的拖拽区域组件
class DragDropWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 设置样式
        self.setStyleSheet("""
            QLabel {
                background-color: #F0F7FF;
                border: 2px dashed #6E3DFF;
                border-radius: 8px;
                color: #555555;
                font: 14px 'Microsoft YaHei UI';
                padding: 20px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setText("拖拽文件到此处\n或点击上方'选择文件'按钮")
        
        self.file_info = ""
        self.is_dragging = False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    background-color: #e5f0ff;
                    border: 2px dashed #4A25AA;
                    border-radius: 8px;
                    color: #333333;
                    font: 14px 'Microsoft YaHei UI';
                    padding: 20px;
                }
            """)
            self.is_dragging = True

    def dragLeaveEvent(self, event):
        self.reset_style()
        self.is_dragging = False

    def dropEvent(self, event: QDropEvent):
        self.reset_style()
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            # 正确的父级访问方式
            self.window().process_file(files[0])
            
            self.file_info = f"已选择文件:\n{os.path.basename(files[0])}"
            self.setText(self.file_info)

    def reset_style(self):
        self.setStyleSheet("""
            QLabel {
                background-color: #F0F7FF;
                border: 2px dashed #6E3DFF;
                border-radius: 8px;
                color: #555555;
                font: 14px 'Microsoft YaHei UI';
                padding: 20px;
            }
        """)
        if self.file_info:
            self.setText(self.file_info)
        else:
            self.setText("拖拽文件到此处\n或点击上方'选择文件'按钮")

# 主应用程序窗口
class BinConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aries")
        self.setMinimumSize(800, 600)
        
        # 样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #E5F0FF;
                color: #333333;
                padding: 8px 15px;
                margin: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font: 12px 'Microsoft YaHei UI';
            }
            QTabBar::tab:selected {
                background: #6E3DFF;
                color: white;
            }
            QPlainTextEdit {
                font-family: 'Cascadia Mono', Consolas, monospace;
                font-size: 11px;
                background-color: #F8FBFF;
                border-radius: 6px;
                border: 1px solid #DDDDDD;
            }
        """)
        
        # 预加载数据缓存
        self.conversion_results = {}
        self.file_data = None
        self.current_tab_index = 0
        
        self.setup_ui()

    def paintEvent(self, event):
        # 绘制渐变背景 - 匹配图片中的蓝白渐变
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor(240, 245, 255))
        grad.setColorAt(1, QColor(230, 240, 255))
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        painter.fillPath(path, grad)

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 标题区域 
        title_label = QLabel("shellcode转换工具")
        title_label.setStyleSheet("""
            QLabel {
                font: bold 24px 'Microsoft YaHei UI';
                color: #333333;
                padding-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 文件选择区域 
        file_layout = QHBoxLayout()
        file_label = QLabel("选择二进制文件:")
        file_label.setStyleSheet("font: 14px 'Microsoft YaHei UI'; color: #333333;")
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("""
            QLabel {
                font: 13px 'Microsoft YaHei UI';
                color: #555555;
                background-color: #F8FBFF;
                border-radius: 6px;
                padding: 8px;
                min-width: 300px;
                border: 1px solid #DDDDDD;
            }
        """)
        self.file_path_label.setFixedHeight(40)
        
        select_btn = RoundedButton("选择文件")
        select_btn.clicked.connect(self.select_file)
        select_btn.setFixedSize(120, 40)
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(select_btn)
        main_layout.addLayout(file_layout)

        # 拖拽区域 
        self.drag_drop_widget = DragDropWidget()
        main_layout.addWidget(self.drag_drop_widget)

        # 转换按钮 
        self.convert_btn = RoundedButton("转  换")
        self.convert_btn.setFixedHeight(50)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #6E3DFF;
                font: bold 14px 'Microsoft YaHei UI';
            }
        """)
        self.convert_btn.clicked.connect(self.convert_file)
        main_layout.addWidget(self.convert_btn)

        # 结果标签页 
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabBar::tab { 
                height: 32px; 
                min-width: 80px; 
                font: 12px 'Microsoft YaHei UI';
            }
            QTabBar::tab:selected {
                background: #6E3DFF;
                color: white;
            }
        """)
        
        # 创建语言标签页 
        self.languages = {
            "C/C++": self.create_tab(),
            "Go 字节数组": self.create_tab(),
            "Go 字符串": self.create_tab(),
            "Python": self.create_tab(),
            "Rust": self.create_tab()
        }
        
        # 标签页切换事件处理
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        for lang, widget in self.languages.items():
            self.tab_widget.addTab(widget, lang)
        
        main_layout.addWidget(self.tab_widget, 1)
        
        # 底部版权信息 
        footer = QLabel("公众号 · DeepDarkSec")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            QLabel {
                color: #888888;
                font: 12px 'Microsoft YaHei UI';
                padding-top: 10px;
            }
        """)
        main_layout.addWidget(footer)

        self.setCentralWidget(main_widget)

    def create_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 使用QPlainTextEdit替代QTextEd
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(text_edit, 1)
        
        # 复制按钮 
        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #6E3DFF;
                color: white;
                border-radius: 6px;
                padding: 8px;
                font: 12px 'Microsoft YaHei UI';
            }
            QPushButton:hover { 
                background-color: #5D30E0; 
            }
        """)
        copy_btn.setFixedHeight(36)
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(text_edit))
        layout.addWidget(copy_btn)
        
        return tab

    def copy_to_clipboard(self, text_edit):
        clipboard = QApplication.clipboard()
        clipboard.setText(text_edit.toPlainText())
        QMessageBox.information(self, "复制成功", "内容已复制到剪贴板！", QMessageBox.Ok)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择二进制文件", "", "二进制文件 (*.bin *.exe *.dll);;所有文件 (*.*)"
        )
        if file_path:
            self.process_file(file_path)

    def process_file(self, file_path):
        self.file_path_label.setText(file_path)
        self.current_file = file_path
        
        # 更新拖拽区域显示 
        self.drag_drop_widget.file_info = f"已选择文件:\n{os.path.basename(file_path)}"
        self.drag_drop_widget.setText(self.drag_drop_widget.file_info)
        
        # 读取文件内容
        try:
            with open(file_path, 'rb') as f:
                self.file_data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "读取错误", f"无法读取文件:\n{str(e)}", QMessageBox.Ok)
            self.file_data = None

    def convert_file(self):
        """优化转换逻辑解决卡顿问题"""
        if not hasattr(self, 'current_file') or not self.current_file:
            QMessageBox.warning(self, "未选择文件", "请先选择二进制文件！", QMessageBox.Ok)
            return
        
        if not self.file_data:
            QMessageBox.critical(self, "文件错误", "未读取到文件内容，请重新选择文件", QMessageBox.Ok)
            return
        
        # 创建进度对话框 (避免UI冻结)
        progress = QProgressDialog("正在转换文件...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)  # 不能取消
        progress.setMinimumDuration(0)
        progress.setWindowTitle("文件转换中")
        progress.show()
        QApplication.processEvents()  # 立即显示进度框
        
        # 创建转换线程
        self.thread = QThread()
        self.worker = ConversionWorker(self.file_data)
        self.worker.moveToThread(self.thread)
        
        # 连接信号
        self.worker.completed.connect(self.on_conversion_completed)
        self.thread.started.connect(self.worker.run)
        
        # 错误处理
        self.thread.finished.connect(self.thread.deleteLater)
        
        # 启动线程
        self.thread.start()
        
        # 完成时关闭进度框
        self.worker.completed.connect(progress.close)

    def on_conversion_completed(self, results):
        """转换完成处理"""
        self.conversion_results = results
        
        # 立即更新当前标签页内容
        current_lang = self.tab_widget.tabText(self.tab_widget.currentIndex())
        if current_lang in self.conversion_results:
            self.update_tab_content(current_lang)
        
        # 成功提示
        QMessageBox.information(
            self, 
            "转换成功", 
            f"文件已成功转换为5种编程语言格式！\n文件大小: {len(self.file_data)} 字节",
            QMessageBox.Ok
        )
    
    def update_tab_content(self, lang):
        """优化更新标签页内容的方法"""
        if lang not in self.conversion_results:
            return
            
        tab = self.languages[lang]
        text_edit = tab.findChild(QPlainTextEdit)
        if not text_edit:
            return
            
        # 使用QPlainTextEdit的appendPlainText方法分块加载
        text_edit.clear()
        content = self.conversion_results[lang]
        
        # 分块加载文本（每1000行加载一次）
        lines = content.split('\n')
        chunk_size = 1000
        total_chunks = (len(lines) + chunk_size - 1) // chunk_size
        
        # 显示加载进度
        progress = QProgressDialog(f"正在加载 {lang} 内容...", None, 0, total_chunks, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        
        # 分块加载文本
        for i in range(0, len(lines), chunk_size):
            chunk = '\n'.join(lines[i:i+chunk_size])
            text_edit.appendPlainText(chunk)
            progress.setValue(i // chunk_size)
            QApplication.processEvents()
        
        # 滚动到顶部
        text_edit.moveCursor(QTextCursor.Start)
        text_edit.ensureCursorVisible()
        
        progress.close()
    
    def on_tab_changed(self, index):
        """标签页切换时的优化处理 - 解决卡顿问题"""
        if not self.conversion_results:
            return
        
        lang = self.tab_widget.tabText(index)
        
        # 如果已经转换过，直接从缓存中获取
        if lang in self.conversion_results:
            self.update_tab_content(lang)

    def closeEvent(self, event):
        """安全退出应用"""
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(1000)  # 等待1秒线程结束
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    
    win = BinConverterApp()
    win.show()
    sys.exit(app.exec_())
