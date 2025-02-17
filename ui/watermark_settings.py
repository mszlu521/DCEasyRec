from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QLineEdit, QSpinBox, QColorDialog, QFileDialog,
                              QGroupBox, QRadioButton, QSlider)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QImage, QPixmap
import os

class WatermarkSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("ScreenRecorder", "Watermark")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        self.setWindowTitle("水印设置")
        layout = QVBoxLayout(self)

        # 水印类型选择
        type_group = QGroupBox("水印类型")
        type_layout = QHBoxLayout()
        self.text_radio = QRadioButton("文字水印")
        self.image_radio = QRadioButton("图片水印")
        type_layout.addWidget(self.text_radio)
        type_layout.addWidget(self.image_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 文字水印设置
        text_group = QGroupBox("文字水印设置")
        text_layout = QVBoxLayout()
        
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("水印文字:"))
        self.text_edit = QLineEdit()
        self.text_edit.setText(self.settings.value("text", ""))
        text_input_layout.addWidget(self.text_edit)
        text_layout.addLayout(text_input_layout)
        
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(int(self.settings.value("size", 24)))
        font_size_layout.addWidget(self.font_size)
        text_layout.addLayout(font_size_layout)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)

        # 图片水印设置
        image_group = QGroupBox("图片水印设置")
        image_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setText(self.settings.value("image_path", ""))
        path_layout.addWidget(self.path_edit)
        
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_image)
        path_layout.addWidget(browse_button)
        image_layout.addLayout(path_layout)
        
        # 图片预览
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(200, 100)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc;")
        image_layout.addWidget(self.preview_label)
        
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # 通用设置
        common_group = QGroupBox("通用设置")
        common_layout = QVBoxLayout()
        
        # 透明度设置
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        
        # 从设置中读取透明度值
        opacity = self.settings.value("opacity", 0.5)  # 默认值改为浮点数
        try:
            # 尝试将字符串转换为浮点数
            opacity = float(opacity)
        except (ValueError, TypeError):
            opacity = 0.5  # 如果转换失败，使用默认值
            
        # 将 0-1 的浮点数转换为 0-100 的整数
        self.opacity_slider.setValue(int(opacity * 100))
        
        self.opacity_value = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_value.setText(f"{v}%"))
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_value)
        common_layout.addLayout(opacity_layout)
        
        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # 确定取消按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 连接信号
        self.text_radio.toggled.connect(self._on_type_changed)
        self.image_radio.toggled.connect(self._on_type_changed)

    def _browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择水印图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.path_edit.setText(file_path)
            self._update_preview(file_path)

    def _update_preview(self, image_path):
        """更新图片预览"""
        if image_path and os.path.exists(image_path):
            image = QImage(image_path)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("图片加载失败")
        else:
            self.preview_label.setText("无图片")

    def _on_type_changed(self, checked):
        is_text = self.text_radio.isChecked()
        self.text_edit.setEnabled(is_text)
        self.font_size.setEnabled(is_text)
        self.path_edit.setEnabled(not is_text)
        self.preview_label.setEnabled(not is_text)

    def load_settings(self):
        watermark_type = self.settings.value("type", "text")
        if watermark_type == "text":
            self.text_radio.setChecked(True)
            self.text_edit.setText(self.settings.value("text", ""))
            self.font_size.setValue(int(self.settings.value("size", 24)))
        else:
            self.image_radio.setChecked(True)
            image_path = self.settings.value("image_path", "")
            self.path_edit.setText(image_path)
            self._update_preview(image_path)
                
        # 修改透明度值的处理
        opacity = self.settings.value("opacity", 0.5)  # 默认值改为浮点数
        try:
            # 尝试将字符串转换为浮点数
            opacity = float(opacity)
        except (ValueError, TypeError):
            opacity = 0.5  # 如果转换失败，使用默认值
            
        # 将 0-1 的浮点数转换为 0-100 的整数
        self.opacity_slider.setValue(int(opacity * 100))

    def save_settings(self):
        self.settings.setValue("type", "text" if self.text_radio.isChecked() else "image")
        self.settings.setValue("text", self.text_edit.text())
        self.settings.setValue("size", self.font_size.value())
        self.settings.setValue("image_path", self.path_edit.text())
        # 将 0-100 的整数转换为 0-1 的浮点数
        self.settings.setValue("opacity", self.opacity_slider.value() / 100) 