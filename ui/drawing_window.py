from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, 
                              QColorDialog, QSpinBox, QLabel, QPushButton,
                              QInputDialog, QApplication)
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import (QPainter, QPen, QColor, QPixmap, QPainterPath, 
                          QFont, QFontMetrics, QCursor)
import numpy as np

class DrawingWindow(QWidget):
    # 添加关闭信号
    closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 首先初始化所有属性
        self.is_locked = False
        self.drawing = False
        self.last_point = None
        self.current_point = None
        self.current_tool = "pen"
        self.current_color = QColor(255, 0, 0)
        self.pen_width = 2
        self.font_size = 12
        self.tools = {}
        
        # 设置窗口标志
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 获取主屏幕尺寸
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # 创建绘图层
        self.drawing_pixmap = QPixmap(screen.width(), screen.height())
        self.drawing_pixmap.fill(Qt.transparent)
        
        # 创建工具栏窗口
        self.toolbar_widget = QWidget(self)
        self.toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid gray;
                border-radius: 5px;
            }
            QPushButton {
                min-width: 60px;
                padding: 5px;
                margin: 2px;
            }
        """)
        
        # 创建工具栏布局
        toolbar_layout = QHBoxLayout(self.toolbar_widget)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        toolbar_layout.setSpacing(5)
        
        # 添加工具按钮
        self.tools = {}
        
        # 画笔工具
        pen_btn = QPushButton("画笔")
        pen_btn.clicked.connect(lambda: self.set_tool("pen"))
        toolbar_layout.addWidget(pen_btn)
        self.tools["pen"] = pen_btn
        
        # 直线工具
        line_btn = QPushButton("直线")
        line_btn.clicked.connect(lambda: self.set_tool("line"))
        toolbar_layout.addWidget(line_btn)
        self.tools["line"] = line_btn
        
        # 矩形工具
        rect_btn = QPushButton("矩形")
        rect_btn.clicked.connect(lambda: self.set_tool("rect"))
        toolbar_layout.addWidget(rect_btn)
        self.tools["rect"] = rect_btn
        
        # 圆形工具
        circle_btn = QPushButton("圆形")
        circle_btn.clicked.connect(lambda: self.set_tool("circle"))
        toolbar_layout.addWidget(circle_btn)
        self.tools["circle"] = circle_btn
        
        # 箭头工具
        arrow_btn = QPushButton("箭头")
        arrow_btn.clicked.connect(lambda: self.set_tool("arrow"))
        toolbar_layout.addWidget(arrow_btn)
        self.tools["arrow"] = arrow_btn
        
        # 文本工具
        text_btn = QPushButton("文本")
        text_btn.clicked.connect(lambda: self.set_tool("text"))
        toolbar_layout.addWidget(text_btn)
        self.tools["text"] = text_btn
        
        toolbar_layout.addSpacing(10)
        
        # 颜色选择器
        color_btn = QPushButton("颜色")
        color_btn.clicked.connect(self.choose_color)
        toolbar_layout.addWidget(color_btn)
        
        # 线宽选择
        toolbar_layout.addWidget(QLabel("线宽:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(2)
        self.width_spin.valueChanged.connect(lambda v: setattr(self, 'pen_width', v))
        toolbar_layout.addWidget(self.width_spin)
        
        # 添加文字大小选择
        toolbar_layout.addWidget(QLabel("文字大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(lambda v: setattr(self, 'font_size', v))
        toolbar_layout.addWidget(self.font_size_spin)
        
        toolbar_layout.addSpacing(10)
        
        # 添加锁定按钮
        self.lock_btn = QPushButton("锁定绘图")
        self.lock_btn.clicked.connect(lambda: self._toggle_lock(True))  # 初始连接到锁定功能
        toolbar_layout.addWidget(self.lock_btn)
        
        # 清除按钮
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self.clear_canvas)
        toolbar_layout.addWidget(clear_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        toolbar_layout.addWidget(close_btn)
        
        # 设置工具栏位置和大小
        toolbar_width = min(1200, screen.width() - 20)
        self.toolbar_widget.setFixedWidth(toolbar_width)
        self.toolbar_widget.setFixedHeight(50)
        self.toolbar_widget.move((screen.width() - toolbar_width) // 2, 10)
        
        # 更新工具按钮状态
        self.update_tool_buttons()
        
        # 最后显示工具栏
        self.toolbar_widget.show()
        
    def set_tool(self, tool):
        self.current_tool = tool
        self.update_tool_buttons()
        
    def update_tool_buttons(self):
        for tool, btn in self.tools.items():
            btn.setStyleSheet("background-color: %s" % 
                            ("#e0e0e0" if tool == self.current_tool else "white"))
        
    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            
    def clear_canvas(self):
        self.drawing_pixmap.fill(Qt.transparent)
        self.update()
        
    def _toggle_lock(self, checked):
        self.is_locked = checked
        if checked:
            # 锁定状态：使用组合标志实现穿透
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.lock_btn.setText("解除锁定")
            
            # 将工具栏设为独立窗口并保持在顶部
            old_pos = self.toolbar_widget.mapToGlobal(QPoint(0, 0))
            self.toolbar_widget.setParent(None)
            self.toolbar_widget.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool)
            
            # 移动到原来的位置
            self.toolbar_widget.move(old_pos)
            self.toolbar_widget.show()
            
            # 重新连接按钮事件
            try:
                self.lock_btn.clicked.disconnect()
            except:
                pass
            self.lock_btn.clicked.connect(lambda: self._toggle_lock(False))
            
            # 重要：需要重新显示窗口以应用新的标志
            self.hide()
            self.show()
        else:
            # 解除锁定：恢复正常模式
            # 先重置所有窗口标志和属性
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.lock_btn.setText("锁定绘图")
            
            # 保存工具栏当前位置
            old_pos = self.toolbar_widget.mapToGlobal(QPoint(0, 0))
            
            # 恢复工具栏为子窗口
            self.toolbar_widget.setParent(self)
            self.toolbar_widget.setWindowFlags(Qt.Widget)
            
            # 计算相对于父窗口的位置
            local_pos = self.mapFromGlobal(old_pos)
            self.toolbar_widget.move(local_pos)
            
            # 重新连接按钮事件
            try:
                self.lock_btn.clicked.disconnect()
            except:
                pass
            self.lock_btn.clicked.connect(lambda: self._toggle_lock(True))
            
            # 重要：需要重新显示窗口以应用新的标志
            self.hide()
            self.show()
            self.toolbar_widget.show()
            self.toolbar_widget.raise_()
            
            # 激活窗口
            self.activateWindow()
            self.setFocus()
            
            # 强制更新窗口状态
            self.repaint()

    def enterEvent(self, event):
        # 不再需要处理工具栏的显示/隐藏
        pass
            
    def leaveEvent(self, event):
        # 不再需要处理工具栏的显示/隐藏
        pass
        
    def showEvent(self, event):
        super().showEvent(event)
        # 确保工具栏显示在正确位置
        if not self.is_locked:
            self.toolbar_widget.show()
            self.toolbar_widget.raise_()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_locked:
            self.drawing = True
            self.last_point = event.pos()
            self.current_point = event.pos()
            
            if self.current_tool == "text":
                text, ok = QInputDialog.getText(self, "输入文字", "请输入要添加的文字:")
                if ok and text:
                    painter = QPainter(self.drawing_pixmap)
                    painter.setPen(QPen(self.current_color, self.pen_width))
                    font = QFont("Arial", self.font_size)
                    painter.setFont(font)
                    painter.drawText(event.pos(), text)
                    self.update()
                self.drawing = False
            
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drawing and not self.is_locked:
            self.current_point = event.pos()
            
            if self.current_tool == "pen":
                painter = QPainter(self.drawing_pixmap)
                painter.setPen(QPen(self.current_color, self.pen_width, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(self.last_point, self.current_point)
                self.last_point = self.current_point
                
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing and not self.is_locked:
            painter = QPainter(self.drawing_pixmap)
            painter.setPen(QPen(self.current_color, self.pen_width, Qt.SolidLine, Qt.RoundCap))
            
            if self.current_tool == "line":
                painter.drawLine(self.last_point, event.pos())
            elif self.current_tool == "rect":
                painter.drawRect(QRect(self.last_point, event.pos()).normalized())
            elif self.current_tool == "circle":
                painter.drawEllipse(QRect(self.last_point, event.pos()).normalized())
            elif self.current_tool == "arrow":
                self.draw_arrow(painter, self.last_point, event.pos())
                
            self.drawing = False
            self.update()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制半透明背景（只在非锁定状态下）
        if not self.is_locked:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 10))
            
        # 绘制画布内容
        painter.drawPixmap(0, 0, self.drawing_pixmap)
        
        # 绘制预览（只在非锁定状态下）
        if not self.is_locked and self.drawing and self.last_point and self.current_point:
            painter.setPen(QPen(self.current_color, self.pen_width, Qt.SolidLine, Qt.RoundCap))
            
            if self.current_tool == "pen":
                painter.drawLine(self.last_point, self.current_point)
            elif self.current_tool == "line":
                painter.drawLine(self.last_point, self.current_point)
            elif self.current_tool == "rect":
                painter.drawRect(QRect(self.last_point, self.current_point).normalized())
            elif self.current_tool == "circle":
                painter.drawEllipse(QRect(self.last_point, self.current_point).normalized())
            elif self.current_tool == "arrow":
                self.draw_arrow(painter, self.last_point, self.current_point)
                
    def draw_arrow(self, painter, start, end):
        # 画箭头主线
        painter.drawLine(start, end)
        
        # 计算箭头
        angle = np.arctan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 20
        arrow_angle = np.pi / 6  # 30度
        
        # 计算箭头两个点
        p1 = QPoint(
            int(end.x() - arrow_size * np.cos(angle - arrow_angle)),
            int(end.y() - arrow_size * np.sin(angle - arrow_angle))
        )
        p2 = QPoint(
            int(end.x() - arrow_size * np.cos(angle + arrow_angle)),
            int(end.y() - arrow_size * np.sin(angle + arrow_angle))
        )
        
        # 画箭头
        painter.drawLine(end, p1)
        painter.drawLine(end, p2)

    def closeEvent(self, event):
        # 发送关闭信号
        self.closed.emit()
        super().closeEvent(event) 