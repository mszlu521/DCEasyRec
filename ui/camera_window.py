from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter
import cv2
import numpy as np

class CameraWindow(QWidget):
    def __init__(self, camera_id=0, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 移除透明背景，否则可能导致图像不显示
        # self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 摄像头图像显示标签
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(320, 240)
        self.layout.addWidget(self.camera_label)
        
        # 摄像头设置
        self.camera_id = camera_id
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # 拖动相关
        self.dragging = False
        self.offset = None
        
        # 美颜设置
        self.beauty_enabled = False
        self.smooth_value = 50
        self.whitening_value = 50
        
        # 设置窗口大小
        self.setFixedSize(320, 240)
        
    def start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_id)
            self.timer.start(33)  # ~30 FPS
            
    def stop_camera(self):
        if self.cap is not None:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            
    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if ret:
            # 水平翻转图像（镜像效果）
            frame = cv2.flip(frame, 1)
            
            # 调整图像大小
            frame = cv2.resize(frame, (320, 240))
            
            # 应用美颜效果
            if self.beauty_enabled:
                frame = self.apply_beauty_filter(frame)
            
            # 转换为 Qt 图像
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # 更新标签显示
            self.camera_label.setPixmap(QPixmap.fromImage(qt_image))
        
    def apply_beauty_filter(self, frame):
        if not self.beauty_enabled:
            return frame
            
        frame = frame.copy()
        
        # 磨皮
        if self.smooth_value > 0:
            smooth_level = self.smooth_value / 100.0
            
            # 双边滤波 - 保留边缘的平滑
            d = int(5 + smooth_level * 3)
            sigma_color = 25 + smooth_level * 30
            sigma_space = 25 + smooth_level * 30
            
            # 多级双边滤波，逐步细化
            temp1 = cv2.bilateralFilter(frame, d, sigma_color, sigma_space)
            temp2 = cv2.bilateralFilter(temp1, d, sigma_color//2, sigma_space//2)
            
            # 提取细节层
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detail_mask = cv2.Laplacian(gray, cv2.CV_8U, ksize=3)
            detail_mask = cv2.GaussianBlur(detail_mask, (3,3), 0)
            
            # 计算混合权重
            weight = 1.0 - (smooth_level * 0.8)
            
            # 简单混合
            frame = cv2.addWeighted(frame, weight, temp2, 1.0 - weight, 0)
        
        # 美白
        if self.whitening_value > 0:
            whitening_level = self.whitening_value / 100.0
            
            # 转换到 LAB 颜色空间
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 自适应直方图均衡
            clahe = cv2.createCLAHE(clipLimit=2.0 + whitening_level, 
                                  tileGridSize=(8,8))
            l = clahe.apply(l)
            
            # 亮度提升
            brightness_increase = int(whitening_level * 10)
            l = cv2.add(l, brightness_increase)
            
            # 合并通道
            lab = cv2.merge([l, a, b])
            whitened = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # 简单混合
            frame = cv2.addWeighted(frame, 1.0 - whitening_level, whitened, whitening_level, 0)
            
            # 微调色彩
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            
            # 轻微调整饱和度
            s = cv2.multiply(s, 1.0 - whitening_level * 0.15)
            # 轻微提升明度
            v = cv2.add(v, int(whitening_level * 5))
            
            hsv = cv2.merge([h, s, v])
            frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            # 最后的对比度微调
            alpha = 1.0 + whitening_level * 0.1
            beta = int(whitening_level * 3)
            frame = cv2.convertScaleAbs(frame, alpha=float(alpha), beta=beta)
        
        return frame
        
    def update_beauty_settings(self, enabled, smooth, whitening):
        self.beauty_enabled = enabled
        self.smooth_value = smooth
        self.whitening_value = whitening
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and self.offset:
            new_pos = event.globalPos() - self.offset
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
            
    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event) 