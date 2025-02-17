from PySide6.QtWidgets import QDialog, QRubberBand, QWidget
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QApplication

class RegionSelector(QWidget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置全屏大小
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # 初始化选择区域
        self.start_pos = None
        self.current_rect = None
        self.selected_rect = None
        
        self.show()
        
    def paintEvent(self, event):
        if self.current_rect:
            painter = QPainter(self)
            # 设置半透明背景
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            
            # 绘制选择区域
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.current_rect, Qt.transparent)
            
            # 绘制边框
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(Qt.red, 2))
            painter.drawRect(self.current_rect)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.current_rect = QRect(self.start_pos, self.start_pos)
            self.update()
            
    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.current_rect = QRect(self.start_pos, event.pos()).normalized()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.current_rect:
            if self.current_rect.width() > 10 and self.current_rect.height() > 10:
                self.selected_rect = self.current_rect
                self.callback(self.selected_rect)
            else:
                self.callback(None)
            self.close() 