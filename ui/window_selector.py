from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
import win32gui
import win32con
from dataclasses import dataclass

@dataclass
class WindowInfo:
    handle: int
    title: str
    x: int
    y: int
    width: int
    height: int

class WindowSelector(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        
        # 设置全屏大小
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.show()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 获取鼠标位置的窗口
            pos = QCursor.pos()
            hwnd = win32gui.WindowFromPoint((pos.x(), pos.y()))
            
            # 获取窗口信息
            if hwnd and hwnd != win32gui.GetDesktopWindow():
                # 获取窗口标题
                title = win32gui.GetWindowText(hwnd)
                
                # 获取窗口位置和大小
                rect = win32gui.GetWindowRect(hwnd)
                x = rect[0]
                y = rect[1]
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                
                # 确保窗口可见且不是最小化
                if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    window_info = WindowInfo(hwnd, title, x, y, width, height)
                    self.callback(window_info)
                    self.close()
                    return
                    
        self.callback(None)
        self.close() 