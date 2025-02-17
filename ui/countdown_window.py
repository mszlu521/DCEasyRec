from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

class CountdownWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 获取屏幕大小
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 创建倒计时标签
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        
        # 设置字体
        font = QFont()
        font.setPointSize(120)  # 大字体
        font.setBold(True)
        self.countdown_label.setFont(font)
        
        # 设置样式
        self.countdown_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 100);
                border-radius: 50px;
                padding: 50px;
            }
        """)
        
        layout.addWidget(self.countdown_label)
        self.show()
        
    def update_countdown(self, count):
        self.countdown_label.setText(f"{count}\n准备开始录制...")
        
    def mousePressEvent(self, event):
        # 点击任意位置关闭窗口
        self.close() 