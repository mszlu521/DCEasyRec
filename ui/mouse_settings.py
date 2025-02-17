from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QSpinBox, QColorDialog, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor

class MouseSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("鼠标设置")
        self.settings = QSettings("ScreenRecorder", "Mouse")
        
        layout = QVBoxLayout(self)
        
        # 鼠标点击效果
        click_group = QVBoxLayout()
        click_group.addWidget(QLabel("点击效果"))
        
        # 启用点击效果
        self.enable_click = QCheckBox("显示点击效果")
        self.enable_click.setChecked(self.settings.value("enable_click", True, type=bool))
        click_group.addWidget(self.enable_click)
        
        # 点击效果颜色
        color_layout = QHBoxLayout()
        self.click_color_btn = QPushButton()
        self.click_color = QColor(self.settings.value("click_color", "#FF0000"))
        self.update_color_button(self.click_color_btn, self.click_color)
        self.click_color_btn.clicked.connect(self.choose_click_color)
        color_layout.addWidget(QLabel("点击颜色:"))
        color_layout.addWidget(self.click_color_btn)
        click_group.addLayout(color_layout)
        
        # 点击效果大小
        size_layout = QHBoxLayout()
        self.click_size = QSpinBox()
        self.click_size.setRange(10, 100)
        self.click_size.setValue(self.settings.value("click_size", 20, type=int))
        size_layout.addWidget(QLabel("效果大小:"))
        size_layout.addWidget(self.click_size)
        click_group.addLayout(size_layout)
        
        # 点击音效
        sound_layout = QHBoxLayout()
        self.enable_sound = QCheckBox("启用点击音效")
        self.enable_sound.setChecked(self.settings.value("enable_sound", True, type=bool))
        sound_layout.addWidget(self.enable_sound)
        click_group.addLayout(sound_layout)
        
        layout.addLayout(click_group)
        
        # 鼠标轨迹
        trail_group = QVBoxLayout()
        trail_group.addWidget(QLabel("鼠标轨迹"))
        
        # 启用轨迹
        self.enable_trail = QCheckBox("显示鼠标轨迹")
        self.enable_trail.setChecked(self.settings.value("enable_trail", True, type=bool))
        trail_group.addWidget(self.enable_trail)
        
        # 轨迹颜色
        trail_color_layout = QHBoxLayout()
        self.trail_color_btn = QPushButton()
        self.trail_color = QColor(self.settings.value("trail_color", "#0000FF"))
        self.update_color_button(self.trail_color_btn, self.trail_color)
        self.trail_color_btn.clicked.connect(self.choose_trail_color)
        trail_color_layout.addWidget(QLabel("轨迹颜色:"))
        trail_color_layout.addWidget(self.trail_color_btn)
        trail_group.addLayout(trail_color_layout)
        
        # 轨迹宽度
        width_layout = QHBoxLayout()
        self.trail_width = QSpinBox()
        self.trail_width.setRange(1, 10)
        self.trail_width.setValue(self.settings.value("trail_width", 2, type=int))
        width_layout.addWidget(QLabel("轨迹宽度:"))
        width_layout.addWidget(self.trail_width)
        trail_group.addLayout(width_layout)
        
        layout.addLayout(trail_group)
        
        # 鼠标高亮
        highlight_group = QVBoxLayout()
        highlight_group.addWidget(QLabel("鼠标高亮"))
        
        # 启用高亮
        self.enable_highlight = QCheckBox("启用鼠标高亮")
        self.enable_highlight.setChecked(self.settings.value("enable_highlight", True, type=bool))
        highlight_group.addWidget(self.enable_highlight)
        
        # 高亮样式
        style_layout = QHBoxLayout()
        self.highlight_style = QComboBox()
        self.highlight_style.addItems(["圆形光环", "聚光灯", "波纹"])
        current_style = self.settings.value("highlight_style", "圆形光环")
        self.highlight_style.setCurrentText(current_style)
        style_layout.addWidget(QLabel("高亮样式:"))
        style_layout.addWidget(self.highlight_style)
        highlight_group.addLayout(style_layout)
        
        # 高亮大小
        highlight_size_layout = QHBoxLayout()
        self.highlight_size = QSpinBox()
        self.highlight_size.setRange(20, 200)
        self.highlight_size.setValue(self.settings.value("highlight_size", 50, type=int))
        highlight_size_layout.addWidget(QLabel("高亮范围:"))
        highlight_size_layout.addWidget(self.highlight_size)
        highlight_group.addLayout(highlight_size_layout)
        
        layout.addLayout(highlight_group)
        
        # 确定取消按钮
        buttons = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
    def choose_click_color(self):
        color = QColorDialog.getColor(self.click_color, self)
        if color.isValid():
            self.click_color = color
            self.update_color_button(self.click_color_btn, color)
            
    def choose_trail_color(self):
        color = QColorDialog.getColor(self.trail_color, self)
        if color.isValid():
            self.trail_color = color
            self.update_color_button(self.trail_color_btn, color)
            
    def update_color_button(self, button, color):
        style = f"background-color: {color.name()}"
        button.setStyleSheet(style)
        
    def save_settings(self):
        self.settings.setValue("enable_click", self.enable_click.isChecked())
        self.settings.setValue("click_color", self.click_color.name())
        self.settings.setValue("click_size", self.click_size.value())
        self.settings.setValue("enable_sound", self.enable_sound.isChecked())
        
        self.settings.setValue("enable_trail", self.enable_trail.isChecked())
        self.settings.setValue("trail_color", self.trail_color.name())
        self.settings.setValue("trail_width", self.trail_width.value())
        
        self.settings.setValue("enable_highlight", self.enable_highlight.isChecked())
        self.settings.setValue("highlight_style", self.highlight_style.currentText())
        self.settings.setValue("highlight_size", self.highlight_size.value()) 