from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                              QPushButton, QComboBox, QLabel, QGroupBox,
                              QSpinBox, QCheckBox, QMessageBox, QSystemTrayIcon, QMenu, QStyle,
                              QFileDialog, QListWidget, QHBoxLayout, QLineEdit, QToolButton,
                              QKeySequenceEdit, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                              QInputDialog, QDialog, QApplication, QStyleFactory, QScrollArea, QSlider)
from PySide6.QtCore import Qt, QTimer, QThread, QEvent, QMetaObject
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QAction
from core.screen_recorder import ScreenRecorder
from core.settings import Settings
from ui.region_selector import RegionSelector
from ui.camera_window import CameraWindow
from ui.window_selector import WindowSelector
from ui.drawing_window import DrawingWindow
from ui.watermark_settings import WatermarkSettings
from ui.mouse_settings import MouseSettings
from ui.countdown_window import CountdownWindow
import os
import subprocess
import mss
from moviepy import VideoFileClip
from datetime import datetime
import cv2
import keyboard  # 需要安装：pip install keyboard

# 将 LoadingOverlay 类移到 MainWindow 类之前
class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
            }
            QLabel {
                color: white;
                background-color: transparent;
                font-size: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # 加载动画
        self.spinner = QLabel("⏳")
        self.spinner.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.spinner)
        
        # 加载文本
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_label)
        
        # 设置动画
        self.animation = QTimer(self)
        self.animation.timeout.connect(self._update_spinner)
        self.spinner_chars = "⏳⌛"
        self.current_char = 0
        
    def showEvent(self, event):
        super().showEvent(event)
        self.animation.start(500)  # 每500ms更新一次
        
    def hideEvent(self, event):
        super().hideEvent(event)
        self.animation.stop()
        
    def _update_spinner(self):
        self.current_char = (self.current_char + 1) % len(self.spinner_chars)
        self.spinner.setText(self.spinner_chars[self.current_char])
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setGeometry(self.parent().rect())
        
    def show_with_text(self, text):
        self.text_label.setText(text)
        self.show()
        QApplication.processEvents()  # 确保立即显示

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 立即加载必要组件
        self.settings = Settings()
        self.recorder = ScreenRecorder()
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._countdown_tick)
        self.countdown_remaining = 0
        
        # 初始化分页数据
        self.page_size = 10  # 每页显示的数量
        self.current_page = 1
        self.total_pages = 1
        self.all_video_data = []  # 存储所有视频数据
        
        # 初始化快捷键列表
        self.shortcuts = []
        
        # 初始化UI
        self._init_ui()
        
        # 初始化快捷键
        self._update_shortcuts()
        
        # 设置系统托盘
        self._setup_tray_icon()
        
        # 现在可以直接使用 LoadingOverlay 类
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()
        
    def _init_ui(self):
        self.setWindowTitle("屏幕录制工具")
        self.setMinimumSize(800, 500)  # 修改窗口大小
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(5)  # 减小间距
        main_layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_main_page(), "录制")
        self.tab_widget.addTab(self._create_settings_page(), "设置")
        self.tab_widget.addTab(self._create_files_page(), "文件")
        
        # 添加标签页切换事件处理
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        main_layout.addWidget(self.tab_widget)
        
        # 添加加载遮罩
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()
        
        # 设置应用样式
        self.setStyle(QStyleFactory.create('Fusion'))
        
        # 设置全局样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", Arial;
                font-size: 14px;
            }
            
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #1976D2;
            }
            
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            
            QGroupBox {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 24px;
                background-color: white;
            }
            
            QGroupBox::title {
                color: #1976D2;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
            }
            
            QComboBox {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 28px;
                font-size: 13px;
            }
            
            
            QComboBox QAbstractItemView {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            
            QSpinBox, QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px;
                background-color: white;
            }
            
            QSpinBox:hover, QLineEdit:hover {
                border-color: #2196F3;
            }
            
            QTableWidget {
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                gridline-color: #E0E0E0;
            }
            
            QTableWidget::item {
                padding: 8px;
            }
            
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: black;
            }
            
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 8px;
                border: none;
                border-right: 1px solid #E0E0E0;
                border-bottom: 1px solid #E0E0E0;
            }
            
            QTabWidget::pane {
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }
            
            QTabBar::tab {
                background-color: #F5F5F5;
                border: 2px solid #E0E0E0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                border-color: #2196F3;
                color: #2196F3;
            }
            
            QCheckBox {
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #E0E0E0;
                border-radius: 4px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border-color: #2196F3;
            }
            
            QToolButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
            
            QToolButton:hover {
                background-color: #1976D2;
            }
            
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px;
            }
            
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
            
            /* 特殊按钮样式 */
            #start_button {
                background-color: #4CAF50;
                font-size: 16px;
                padding: 12px 24px;
            }
            
            #start_button:hover {
                background-color: #388E3C;
            }
            
            #pause_button {
                background-color: #FFC107;
                color: black;
            }
            
            #pause_button:hover {
                background-color: #FFA000;
            }
            
            #stop_button {
                background-color: #F44336;
            }
            
            #stop_button:hover {
                background-color: #D32F2F;
            }
        """)
        
    def _create_main_page(self):
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)  # 使用水平布局
        
        # 左侧：录制设置和音频设置
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 录制设置组
        recording_group = self._create_recording_group()
        left_layout.addWidget(recording_group)
        
        # 音频设置组
        audio_group = self._create_audio_group()
        left_layout.addWidget(audio_group)
        
        left_layout.addStretch()
        layout.addWidget(left_panel)
        
        # 右侧：摄像头设置和控制按钮
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 摄像头设置组
        camera_group = self._create_camera_group()
        right_layout.addWidget(camera_group)
        
        # 画笔工具按钮
        drawing_group = QGroupBox("画笔工具")
        drawing_layout = QVBoxLayout()
        self.drawing_btn = QPushButton("画笔工具")
        self.drawing_btn.clicked.connect(self._toggle_drawing_window)
        drawing_layout.addWidget(self.drawing_btn)
        drawing_group.setLayout(drawing_layout)
        right_layout.addWidget(drawing_group)
        
        # 控制按钮组
        control_group = self._create_control_group()
        right_layout.addWidget(control_group)
        
        right_layout.addStretch()
        layout.addWidget(right_panel)
        
        return main_widget
        
    def _create_settings_page(self):
        settings_widget = QWidget()
        layout = QHBoxLayout(settings_widget)  # 使用水平布局
        
        # 左侧：基本设置和快捷键设置
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 基本设置组
        basic_group = self._create_basic_settings_group()
        left_layout.addWidget(basic_group)
        
        # 快捷键设置组
        shortcut_group = self._create_shortcut_settings_group()
        left_layout.addWidget(shortcut_group)
        
        left_layout.addStretch()
        layout.addWidget(left_panel)
        
        # 右侧：输出设置、水印设置和鼠标设置
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 输出设置组
        output_group = self._create_output_settings_group()
        right_layout.addWidget(output_group)
        
        # 水印和鼠标设置组
        watermark_mouse_group = self._create_watermark_mouse_settings_group()
        right_layout.addWidget(watermark_mouse_group)
        
        right_layout.addStretch()
        layout.addWidget(right_panel)
        
        return settings_widget
        
    def _create_files_page(self):
        files_widget = QWidget()
        layout = QVBoxLayout(files_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 工具栏（直接使用水平布局，不使用 GroupBox）
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                min-height: 28px;
                padding: 5px 15px;
                background-color: #2196F3;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #90CAF9;
                color: #E3F2FD;
            }
        """
        
        refresh_button = QPushButton("刷新列表")
        refresh_button.setStyleSheet(button_style)
        refresh_button.clicked.connect(self._update_video_list)
        
        open_folder_button = QPushButton("打开文件夹")
        open_folder_button.setStyleSheet(button_style)
        open_folder_button.clicked.connect(self._open_video_folder)
        
        # 分页控件
        self.page_label = QLabel("页码: 1/1")
        self.page_label.setStyleSheet("font-size: 13px;")
        
        prev_page = QPushButton("上一页")
        next_page = QPushButton("下一页")
        prev_page.setStyleSheet(button_style)
        next_page.setStyleSheet(button_style)
        prev_page.clicked.connect(self._prev_page)
        next_page.clicked.connect(self._next_page)
        
        toolbar_layout.addWidget(refresh_button)
        toolbar_layout.addWidget(open_folder_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(prev_page)
        toolbar_layout.addWidget(self.page_label)
        toolbar_layout.addWidget(next_page)
        
        layout.addLayout(toolbar_layout)  # 直接添加布局，不使用 GroupBox
        
        # 视频列表组
        video_list_group = QGroupBox("视频列表")
        video_list_layout = QVBoxLayout()
        
        # 创建表格
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(5)
        self.video_table.setHorizontalHeaderLabels(["名称", "时长", "大小", "创建时间", "操作"])
        
        # 设置表格样式
        self.video_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                selection-background-color: #e9ecef;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 0px;
                height: 24px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #dee2e6;
                font-weight: bold;
                font-size: 13px;
            }
            QToolButton {
                min-width: 70px;
                min-height: 14px;
                padding: 1px;
                font-size: 13px;
                border: 1px solid #dee2e6;
                border-radius: 2px;
                background-color: #f8f9fa;
                color: #212529;
            }
            QToolButton:hover {
                background-color: #e9ecef;
                border-color: #ced4da;
            }
            QMenu {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 25px;
                color: #212529;
            }
            QMenu::item:selected {
                background-color: #e9ecef;
            }
        """)
        
        # 设置列宽
        header = self.video_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        self.video_table.setColumnWidth(0, 300)  # 增加文件名列宽度
        
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        self.video_table.setColumnWidth(1, 80)
        self.video_table.setColumnWidth(2, 80)
        self.video_table.setColumnWidth(3, 150)
        self.video_table.setColumnWidth(4, 80)
        
        video_list_layout.addWidget(self.video_table)
        video_list_group.setLayout(video_list_layout)
        layout.addWidget(video_list_group)
        
        return files_widget

    def _update_shortcut(self, shortcut_type):
        if shortcut_type == 'start':
            self.settings.set_shortcut_start(self.shortcut_start.keySequence().toString())
        elif shortcut_type == 'pause':
            self.settings.set_shortcut_pause(self.shortcut_pause.keySequence().toString())
        elif shortcut_type == 'stop':
            self.settings.set_shortcut_stop(self.shortcut_stop.keySequence().toString())
        elif shortcut_type == 'drawing':
            self.settings.set_shortcut_drawing(self.shortcut_drawing.keySequence().toString())
        
        self._update_shortcuts()
        
    def _update_shortcuts(self):
        # 移除旧的快捷键
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts.clear()
        
        # 添加新的快捷键
        start_sequence = QKeySequence(self.settings.get_shortcut_start())
        pause_sequence = QKeySequence(self.settings.get_shortcut_pause())
        stop_sequence = QKeySequence(self.settings.get_shortcut_stop())
        drawing_sequence = QKeySequence(self.settings.get_shortcut_drawing())
        
        # 创建快捷键
        start_shortcut = QShortcut(start_sequence, self)
        pause_shortcut = QShortcut(pause_sequence, self)
        stop_shortcut = QShortcut(stop_sequence, self)
        drawing_shortcut = QShortcut(drawing_sequence, self)
        
        # 连接信号
        start_shortcut.activated.connect(self.start_recording)
        pause_shortcut.activated.connect(self.pause_recording)
        stop_shortcut.activated.connect(self.stop_recording)
        drawing_shortcut.activated.connect(self._toggle_drawing_window)
        
        # 保存快捷键引用
        self.shortcuts.extend([
            start_shortcut,
            pause_shortcut,
            stop_shortcut,
            drawing_shortcut
        ])

    def _trigger_start_recording(self):
        try:
            print("触发开始录制快捷键")  # 调试信息
            QMetaObject.invokeMethod(
                self,
                "start_recording",
                Qt.QueuedConnection
            )
        except Exception as e:
            print(f"开始录制触发失败: {e}")  # 调试信息

    def _trigger_pause_recording(self):
        try:
            print("触发暂停快捷键")  # 调试信息
            QApplication.instance().postEvent(
                self,
                self.QPauseRecordingEvent()  # 自定义事件
            )
        except Exception as e:
            print(f"暂停录制触发失败: {e}")  # 调试信息

    def _trigger_stop_recording(self):
        try:
            print("触发停止快捷键")  # 调试信息
            QApplication.instance().postEvent(
                self,
                self.QStopRecordingEvent()  # 自定义事件
            )
        except Exception as e:
            print(f"停止录制触发失败: {e}")  # 调试信息

    # 添加自定义事件类
    class QStartRecordingEvent(QEvent):
        Type = QEvent.Type(QEvent.registerEventType())
        
        def __init__(self):
            super().__init__(self.Type)

    class QPauseRecordingEvent(QEvent):
        Type = QEvent.Type(QEvent.registerEventType())
        
        def __init__(self):
            super().__init__(self.Type)

    class QStopRecordingEvent(QEvent):
        Type = QEvent.Type(QEvent.registerEventType())
        
        def __init__(self):
            super().__init__(self.Type)

    def event(self, event):
        if isinstance(event, self.QStartRecordingEvent):
            self.start_recording()
            return True
        elif isinstance(event, self.QPauseRecordingEvent):
            self.pause_recording()
            return True
        elif isinstance(event, self.QStopRecordingEvent):
            self.stop_recording()
            return True
        return super().event(event)

    def start_recording(self):
        print("快捷键触发：开始录制")
        if self.recorder.recording:
            return
            
        print("执行开始录制")
        # 获取倒计时设置
        countdown = self.settings.get_countdown()
        if countdown > 0:
            self.countdown_remaining = countdown
            self.start_button.setEnabled(False)
            self.countdown_timer.start(1000)
            self.start_button.setText(f"倒计时 {self.countdown_remaining}...")
            
            # 立即隐藏主窗口
            self.hide()
            
            # 显示全屏倒计时窗口
            if not hasattr(self, 'countdown_window'):
                self.countdown_window = CountdownWindow()
            self.countdown_window.update_countdown(self.countdown_remaining)
            return
            
        self._start_recording_with_type()

    def _countdown_tick(self):
        self.countdown_remaining -= 1
        
        # 更新倒计时显示
        if hasattr(self, 'countdown_window'):
            self.countdown_window.update_countdown(self.countdown_remaining)
        
        if self.countdown_remaining > 0:
            self.start_button.setText(f"倒计时 {self.countdown_remaining}...")
        else:
            self.countdown_timer.stop()
            self.start_button.setText("录制中...")
            if hasattr(self, 'countdown_window'):
                self.countdown_window.close()
                delattr(self, 'countdown_window')
            self._start_recording_with_type()

    def _start_recording_with_type(self):
        recording_type = self.recording_type.currentText()
        region = None
        
        if recording_type == "全屏录制":
            # 获取选中的显示器
            monitor = self.monitor_select.currentData()
            if monitor:
                region = {
                    'top': monitor['top'],
                    'left': monitor['left'],
                    'width': monitor['width'],
                    'height': monitor['height']
                }
                self._start_recording_now(region)
        elif recording_type == "窗口录制":
            # 创建窗口选择器
            self.hide()
            QMessageBox.information(self, "选择窗口", "请点击要录制的窗口")
            
            def on_window_selected(window_info):
                if window_info:
                    region = {
                        'top': window_info.y,
                        'left': window_info.x,
                        'width': window_info.width,
                        'height': window_info.height
                    }
                    self._start_recording_now(region)
                else:
                    self.show()
                
            self.window_selector = WindowSelector(on_window_selected)
            
        elif recording_type == "区域录制":
            # 创建区域选择器
            self.hide()
            
            def on_region_selected(rect):
                if rect:
                    region = {
                        'top': rect.top(),
                        'left': rect.left(),
                        'width': rect.width(),
                        'height': rect.height()
                    }
                    self._start_recording_now(region)
                else:
                    self.show()
                
            self.region_selector = RegionSelector(on_region_selected)
        else:
            self._start_recording_now(None)
            
    def _start_recording_now(self, region=None):
        # 生成输出文件路径
        output_file = os.path.join(
            self.settings.get_video_path(),
            self.settings.generate_filename()
        )
        
        # 配置录制参数
        self.recorder.fps = int(self.fps.currentText())
        resolution = self.resolution.currentText().split('x')
        self.recorder.frame_size = (int(resolution[0]), int(resolution[1]))
        
        # 设置音频参数
        self.recorder.audio_source = self.audio_source.currentText()
        self.recorder.system_volume = self.system_volume.value()
        self.recorder.mic_volume = self.mic_volume.value()
        
        # 设置降噪参数
        self.recorder.noise_reduction_enabled = self.noise_reduction_enabled.isChecked()
        self.recorder.noise_reduction_strength = self.noise_reduction_strength.value() / 100.0
        
        # 开始录制
        self.recorder.start_recording(region=region, output_file=output_file)
        
        # 更新UI状态
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        # 自动最小化到系统托盘
        if self.settings.get_auto_hide():
            self.hide()
            self.tray_icon.showMessage(
                "屏幕录制",
                "录制已开始，双击图标显示主窗口",
                QSystemTrayIcon.Information,
                2000
            )
            
        # 如果启用了摄像头，确保摄像头窗口显示
        if self.camera_enabled.isChecked() and not hasattr(self, 'camera_window'):
            self._toggle_camera_window()
        
    def pause_recording(self):
        print("快捷键触发：暂停/继续")  # 调试信息
        if not self.recorder.recording:
            return
            
        if self.recorder.paused:
            self.recorder.resume_recording()
            self.pause_button.setText("暂停")
        else:
            self.recorder.pause_recording()
            self.pause_button.setText("继续")
            
    def stop_recording(self):
        print("快捷键触发：停止录制")  # 调试信息
        if not self.recorder.recording:
            return
            
        # 显示加载提示
        self.loading_overlay.show_with_text("正在生成视频文件...")
        
        output_file = self.recorder.output_file
        self.recorder.stop_recording()
        
        # 使用 QTimer 延迟更新视频列表和显示消息
        def show_completion():
            self._update_video_list()
            self.loading_overlay.hide()  # 隐藏加载提示
            QMessageBox.information(
                self, 
                "录制完成",
                f"录制已完成，文件保存为：\n{output_file}"
            )
            self.tab_widget.setCurrentIndex(2)
            
        QTimer.singleShot(500, show_completion)
        
        # 更新UI状态
        self.start_button.setText("开始录制")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText("暂停")
        
        # 如果窗口被隐藏，则显示
        if not self.isVisible():
            self.show()
        
        # 如果有摄像头窗口，关闭它
        if hasattr(self, 'camera_window'):
            self.camera_window.close()
            delattr(self, 'camera_window')
            self.camera_show_btn.setText("显示摄像头")
        
        # 关闭画笔窗口
        if hasattr(self, 'drawing_window'):
            self.drawing_window.close()
            delattr(self, 'drawing_window')
            self.drawing_btn.setText("画笔工具")

    def _tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            
    def closeEvent(self, event):
        if self.recorder.recording:
            # 如果正在录制，则最小化到托盘
            self.hide()
            self.tray_icon.showMessage(
                "屏幕录制",
                "录制继续在后台进行",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            # 如果没有在录制，则正常退出
            # 清理快捷键
            for shortcut in self.shortcuts:
                shortcut.setEnabled(False)
                shortcut.deleteLater()
            self.tray_icon.hide()
            event.accept()

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择视频保存目录", 
            self.path_edit.text()
        )
        if path:
            self.settings.set_video_path(path)
            self.path_edit.setText(path)
            self._update_video_list()
            
    def _update_video_list(self):
        self.loading_overlay.show_with_text("正在加载视频列表...")
        QTimer.singleShot(0, self._load_all_videos)

    def _load_all_videos(self):
        video_path = self.settings.get_video_path()
        self.all_video_data = []
        
        # 获取所有视频文件信息
        for file in os.listdir(video_path):
            if file.endswith(('.mp4', '.avi', '.mkv')):
                file_path = os.path.join(video_path, file)
                row_data = self._get_video_info(file_path)
                ctime = os.path.getctime(file_path)
                self.all_video_data.append((row_data, file_path, ctime))
        
        # 按创建时间倒序排序
        self.all_video_data.sort(key=lambda x: x[2], reverse=True)
        
        # 计算总页数
        self.total_pages = max(1, (len(self.all_video_data) + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, self.total_pages)
        
        # 更新当前页
        self._update_current_page()
        self.loading_overlay.hide()

    def _update_current_page(self):
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.all_video_data))
        current_page_data = self.all_video_data[start_idx:end_idx]
        
        self.video_table.setRowCount(len(current_page_data))
        for row, (row_data, file_path, ctime) in enumerate(current_page_data):
            # 设置前四列
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                if col == 0:  # 文件名列
                    item.setToolTip(data)  # 添加工具提示
                self.video_table.setItem(row, col, item)
            
            # 创建操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(2)
            
            action_button = QToolButton()
            action_button.setText("操作")
            action_button.setPopupMode(QToolButton.InstantPopup)
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    border: 1px solid #ddd;
                }
                QMenu::item {
                    padding: 5px 20px;
                    color: #333;
                }
                QMenu::item:selected {
                    background-color: #E3F2FD;
                }
            """)
            
            # 创建操作菜单项
            for action_text, callback in [
                ("播放", self._play_video),
                ("重命名", self._rename_video),
                ("删除", self._delete_video),
                ("定位", self._locate_video)
            ]:
                action = menu.addAction(action_text)
                action.triggered.connect(lambda checked, p=file_path, c=callback: c(p))
            
            action_button.setMenu(menu)
            action_layout.addWidget(action_button)
            
            self.video_table.setCellWidget(row, 4, action_widget)
        
        # 更新页码显示
        self.page_label.setText(f"页码: {self.current_page}/{self.total_pages}")

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._update_current_page()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_current_page()

    def _get_video_info(self, file_path):
        """获取视频文件信息"""
        file_name = os.path.basename(file_path)
        row_data = [file_name]
        
        # 获取视频时长
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            result = subprocess.run([
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ], 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='ignore',
            startupinfo=startupinfo
            )
            
            if result.stdout.strip():
                duration = float(result.stdout)
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
            else:
                duration_str = "未知"
        except Exception as e:
            print(f"获取视频时长失败: {e}")
            duration_str = "未知"
            
        row_data.append(duration_str)
        
        # 文件大小
        size = os.path.getsize(file_path)
        if size >= 1024 * 1024 * 1024:  # GB
            size_str = f"{size / 1024 / 1024 / 1024:.1f} GB"
        elif size >= 1024 * 1024:  # MB
            size_str = f"{size / 1024 / 1024:.1f} MB"
        else:  # KB
            size_str = f"{size / 1024:.1f} KB"
        row_data.append(size_str)
        
        # 创建时间
        ctime = os.path.getctime(file_path)
        time_str = datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
        row_data.append(time_str)
        
        return row_data

    def _play_video(self, file_path):
        # 使用系统默认播放器打开视频
        if os.name == 'nt':  # Windows
            os.startfile(file_path)
        else:  # Linux/Mac
            subprocess.run(['xdg-open', file_path])
            
    def _rename_video(self, file_path):
        old_name = os.path.basename(file_path)
        new_name, ok = QInputDialog.getText(
            self, 
            "重命名文件",
            "请输入新的文件名:",
            text=old_name
        )
        
        if ok and new_name:
            try:
                new_path = os.path.join(os.path.dirname(file_path), new_name)
                os.rename(file_path, new_path)
                self._update_video_list()
            except Exception as e:
                QMessageBox.warning(self, "重命名失败", str(e))
                
    def _delete_video(self, file_path):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除文件 {os.path.basename(file_path)} 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                self._update_video_list()
            except Exception as e:
                QMessageBox.warning(self, "删除失败", str(e))
                
    def _locate_video(self, file_path):
        # 打开文件所在文件夹并选中文件
        if os.name == 'nt':  # Windows
            subprocess.run(['explorer', '/select,', file_path])
        else:  # Linux/Mac
            subprocess.run(['xdg-open', os.path.dirname(file_path)])

    def _open_video_folder(self):
        path = self.settings.get_video_path()
        os.startfile(path)

    def _setup_tray_icon(self):
        # 修改系统托盘图标设置
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self.show)
        stop_action = tray_menu.addAction("停止录制")
        stop_action.triggered.connect(self.stop_recording)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 托盘图标双击显示窗口
        self.tray_icon.activated.connect(self._tray_icon_activated)
        
        # 更新托盘提示信息，包含快捷键
        tooltip = "屏幕录制工具\n"
        if self.settings.get_shortcut_start():
            tooltip += f"开始录制: {self.settings.get_shortcut_start()}\n"
        if self.settings.get_shortcut_pause():
            tooltip += f"暂停/继续: {self.settings.get_shortcut_pause()}\n"
        if self.settings.get_shortcut_stop():
            tooltip += f"停止录制: {self.settings.get_shortcut_stop()}"
            
        self.tray_icon.setToolTip(tooltip)

    def _on_tab_changed(self, index):
        # 当切换到文件标签页时，刷新文件列表
        if index == 2:  # 文件页的索引
            self._update_video_list() 

    def _update_camera_list(self):
        self.camera_select.clear()
        # 检测可用摄像头
        for i in range(5):  # 检查前5个摄像头设备
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.camera_select.addItem(f"摄像头 {i}")
                cap.release()
                
    def _on_camera_enabled_changed(self, enabled):
        self.camera_show_btn.setEnabled(enabled)
        if not enabled and hasattr(self, 'camera_window'):
            self.camera_window.close()
            
    def _toggle_camera_window(self):
        if not hasattr(self, 'camera_window'):
            camera_id = self.camera_select.currentIndex()
            self.camera_window = CameraWindow(camera_id)
            self.camera_window.show()
            self.camera_window.start_camera()
            self.camera_show_btn.setText("隐藏摄像头")
        else:
            self.camera_window.close()
            delattr(self, 'camera_window')
            self.camera_show_btn.setText("显示摄像头")

    def _toggle_drawing_window(self):
        if not hasattr(self, 'drawing_window'):
            self.drawing_window = DrawingWindow()
            # 连接关闭信号
            self.drawing_window.closed.connect(self._on_drawing_window_closed)
            self.drawing_window.show()
            self.drawing_btn.setText("关闭画笔")
        else:
            self.drawing_window.close()
            delattr(self, 'drawing_window')
            self.drawing_btn.setText("画笔工具")

    def _on_drawing_window_closed(self):
        # 处理画笔窗口关闭事件
        if hasattr(self, 'drawing_window'):
            delattr(self, 'drawing_window')
            self.drawing_btn.setText("画笔工具")

    def _show_watermark_settings(self):
        dialog = WatermarkSettings(self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_settings()

    def _show_mouse_settings(self):
        dialog = MouseSettings(self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_settings()

    def _update_recording_options(self):
        self.recording_type.clear()
        self.monitor_select.clear()
        
        # 添加录制类型
        self.recording_type.addItems(["全屏录制", "窗口录制", "区域录制"])
        
        # 获取所有显示器
        with mss.mss() as sct:
            for i, monitor in enumerate(sct.monitors[1:], 1):  # 跳过第一个（全部显示器）
                name = f"显示器 {i} ({monitor['width']}x{monitor['height']})"
                self.monitor_select.addItem(name, monitor)
                
    def _on_recording_type_changed(self, index):
        recording_type = self.recording_type.currentText()
        self.monitor_select.setVisible(recording_type == "全屏录制") 

    def _check_shortcut_conflict(self, current_type, sequence):
        # 检查快捷键是否冲突
        if sequence.isEmpty():
            return
            
        sequence_str = sequence.toString()
        if current_type != 'start' and sequence_str == self.settings.get_shortcut_start():
            QMessageBox.warning(self, "快捷键冲突", "此快捷键已被开始录制使用")
            self._reset_shortcut(current_type)
        elif current_type != 'pause' and sequence_str == self.settings.get_shortcut_pause():
            QMessageBox.warning(self, "快捷键冲突", "此快捷键已被暂停/继续使用")
            self._reset_shortcut(current_type)
        elif current_type != 'stop' and sequence_str == self.settings.get_shortcut_stop():
            QMessageBox.warning(self, "快捷键冲突", "此快捷键已被停止录制使用")
            self._reset_shortcut(current_type)

    def _reset_shortcut(self, shortcut_type):
        if shortcut_type == 'start':
            self.shortcut_start.setKeySequence(QKeySequence(self.settings.get_shortcut_start()))
        elif shortcut_type == 'pause':
            self.shortcut_pause.setKeySequence(QKeySequence(self.settings.get_shortcut_pause()))
        elif shortcut_type == 'stop':
            self.shortcut_stop.setKeySequence(QKeySequence(self.settings.get_shortcut_stop()))

    def _create_recording_group(self):
        recording_group = QGroupBox("录制设置")
        recording_layout = QVBoxLayout()
        
        # 录制类型选择
        recording_layout.addWidget(QLabel("录制类型:"))
        self.recording_type = QComboBox()
        self.recording_type.currentIndexChanged.connect(self._on_recording_type_changed)
        recording_layout.addWidget(self.recording_type)
        
        # 显示器选择
        self.monitor_select = QComboBox()
        self.monitor_select.hide()
        recording_layout.addWidget(QLabel("选择显示器:"))
        recording_layout.addWidget(self.monitor_select)
        
        # 分辨率和帧率设置
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("分辨率:"))
        self.resolution = QComboBox()
        self.resolution.addItems(["1920x1080", "1280x720", "3840x2160"])
        resolution_layout.addWidget(self.resolution)
        recording_layout.addLayout(resolution_layout)
        
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("帧率:"))
        self.fps = QComboBox()
        self.fps.addItems(["30", "60"])
        fps_layout.addWidget(self.fps)
        recording_layout.addLayout(fps_layout)
        
        # 更新录制类型和显示器列表
        self._update_recording_options()
        
        recording_group.setLayout(recording_layout)
        return recording_group

    def _create_audio_group(self):
        audio_group = QGroupBox("音频设置")
        audio_layout = QVBoxLayout()
        
        # 音频源选择
        self.audio_source = QComboBox()
        self.audio_source.addItems([
            "系统声音 + 麦克风",
            "仅系统声音",
            "仅麦克风声音",
            "静音"
        ])
        audio_layout.addWidget(QLabel("音频源:"))
        audio_layout.addWidget(self.audio_source)
        
        # 音量控制
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("系统音量:"))
        self.system_volume = QSpinBox()
        self.system_volume.setRange(0, 100)
        self.system_volume.setValue(100)
        self.system_volume.setSuffix("%")
        volume_layout.addWidget(self.system_volume)
        
        mic_volume_layout = QHBoxLayout()
        mic_volume_layout.addWidget(QLabel("麦克风音量:"))
        self.mic_volume = QSpinBox()
        self.mic_volume.setRange(0, 100)
        self.mic_volume.setValue(100)
        self.mic_volume.setSuffix("%")
        mic_volume_layout.addWidget(self.mic_volume)
        
        # 降噪设置
        noise_reduction_group = QGroupBox("降噪设置")
        noise_reduction_layout = QVBoxLayout()
        
        # 降噪开关
        self.noise_reduction_enabled = QCheckBox("启用降噪")
        noise_reduction_layout.addWidget(self.noise_reduction_enabled)
        
        # 降噪强度
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("降噪强度:"))
        self.noise_reduction_strength = QSlider(Qt.Horizontal)
        self.noise_reduction_strength.setRange(0, 100)
        self.noise_reduction_strength.setValue(50)
        self.noise_reduction_value = QLabel("50")
        strength_layout.addWidget(self.noise_reduction_strength)
        strength_layout.addWidget(self.noise_reduction_value)
        noise_reduction_layout.addLayout(strength_layout)
        
        # 连接信号
        self.noise_reduction_strength.valueChanged.connect(
            lambda v: self.noise_reduction_value.setText(str(v)))
        
        noise_reduction_group.setLayout(noise_reduction_layout)
        
        audio_layout.addLayout(volume_layout)
        audio_layout.addLayout(mic_volume_layout)
        audio_layout.addWidget(noise_reduction_group)
        
        audio_group.setLayout(audio_layout)
        return audio_group

    def _create_camera_group(self):
        camera_group = QGroupBox("摄像头设置")
        camera_layout = QVBoxLayout()
        
        # 摄像头启用选项
        self.camera_enabled = QCheckBox("启用摄像头")
        camera_layout.addWidget(self.camera_enabled)
        
        # 摄像头选择
        camera_select_layout = QHBoxLayout()
        camera_select_layout.addWidget(QLabel("选择摄像头:"))
        self.camera_select = QComboBox()
        self._update_camera_list()
        camera_select_layout.addWidget(self.camera_select)
        camera_layout.addLayout(camera_select_layout)
        
        # 美颜设置组
        beauty_group = QGroupBox("美颜设置")
        beauty_layout = QVBoxLayout()
        
        # 美颜开关
        self.beauty_enabled = QCheckBox("启用美颜")
        beauty_layout.addWidget(self.beauty_enabled)
        
        # 磨皮程度
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(QLabel("磨皮程度:"))
        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(0, 100)
        self.smooth_slider.setValue(50)
        self.smooth_value = QLabel("50")
        smooth_layout.addWidget(self.smooth_slider)
        smooth_layout.addWidget(self.smooth_value)
        beauty_layout.addLayout(smooth_layout)
        
        # 美白程度
        whitening_layout = QHBoxLayout()
        whitening_layout.addWidget(QLabel("美白程度:"))
        self.whitening_slider = QSlider(Qt.Horizontal)
        self.whitening_slider.setRange(0, 100)
        self.whitening_slider.setValue(50)
        self.whitening_value = QLabel("50")
        whitening_layout.addWidget(self.whitening_slider)
        whitening_layout.addWidget(self.whitening_value)
        beauty_layout.addLayout(whitening_layout)
        
        # 连接滑块值变化信号
        self.smooth_slider.valueChanged.connect(
            lambda v: self.smooth_value.setText(str(v)))
        self.whitening_slider.valueChanged.connect(
            lambda v: self.whitening_value.setText(str(v)))
        
        # 美颜设置变更时更新摄像头效果
        self.beauty_enabled.toggled.connect(self._update_beauty_settings)
        self.smooth_slider.valueChanged.connect(self._update_beauty_settings)
        self.whitening_slider.valueChanged.connect(self._update_beauty_settings)
        
        beauty_group.setLayout(beauty_layout)
        camera_layout.addWidget(beauty_group)
        
        # 摄像头控制按钮
        self.camera_show_btn = QPushButton("显示摄像头")
        self.camera_show_btn.setEnabled(False)
        self.camera_show_btn.clicked.connect(self._toggle_camera_window)
        camera_layout.addWidget(self.camera_show_btn)
        
        # 连接摄像头启用状态变更
        self.camera_enabled.toggled.connect(self._on_camera_enabled_changed)
        
        camera_group.setLayout(camera_layout)
        return camera_group

    def _update_beauty_settings(self):
        if hasattr(self, 'camera_window'):
            self.camera_window.update_beauty_settings(
                enabled=self.beauty_enabled.isChecked(),
                smooth=self.smooth_slider.value(),
                whitening=self.whitening_slider.value()
            )

    def _create_control_group(self):
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout()
        
        self.start_button = QPushButton("开始录制")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("停止")
        
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        
        # 连接按钮信号
        self.start_button.clicked.connect(self.start_recording)
        self.pause_button.clicked.connect(self.pause_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        
        # 设置控制按钮的 objectName
        self.start_button.setObjectName("start_button")
        self.pause_button.setObjectName("pause_button")
        self.stop_button.setObjectName("stop_button")
        
        control_group.setLayout(control_layout)
        return control_group

    def _create_basic_settings_group(self):
        basic_group = QGroupBox("基本设置")
        basic_layout = QVBoxLayout()
        
        # 倒计时设置
        countdown_layout = QHBoxLayout()
        self.countdown_spin = QSpinBox()
        self.countdown_spin.setRange(0, 10)
        self.countdown_spin.setValue(self.settings.get_countdown())
        countdown_layout.addWidget(QLabel("开始录制倒计时(秒):"))
        countdown_layout.addWidget(self.countdown_spin)
        basic_layout.addLayout(countdown_layout)
        
        # 自动隐藏设置
        self.auto_hide = QCheckBox("录制时自动隐藏窗口")
        self.auto_hide.setChecked(self.settings.get_auto_hide())
        basic_layout.addWidget(self.auto_hide)
        
        # 保存设置变更
        self.countdown_spin.valueChanged.connect(
            lambda v: self.settings.set_countdown(v))
            
        self.auto_hide.toggled.connect(
            lambda v: self.settings.set_auto_hide(v))
            
        basic_group.setLayout(basic_layout)
        return basic_group

    def _create_shortcut_settings_group(self):
        shortcut_group = QGroupBox("快捷键设置")
        shortcut_layout = QVBoxLayout()
        
        # 开始录制快捷键
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("开始录制:"))
        self.shortcut_start = QKeySequenceEdit(self.settings.get_shortcut_start())
        start_layout.addWidget(self.shortcut_start)
        shortcut_layout.addLayout(start_layout)
        
        # 暂停录制快捷键
        pause_layout = QHBoxLayout()
        pause_layout.addWidget(QLabel("暂停/继续:"))
        self.shortcut_pause = QKeySequenceEdit(self.settings.get_shortcut_pause())
        pause_layout.addWidget(self.shortcut_pause)
        shortcut_layout.addLayout(pause_layout)
        
        # 停止录制快捷键
        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel("停止录制:"))
        self.shortcut_stop = QKeySequenceEdit(self.settings.get_shortcut_stop())
        stop_layout.addWidget(self.shortcut_stop)
        shortcut_layout.addLayout(stop_layout)
        
        # 画笔工具快捷键
        drawing_layout = QHBoxLayout()
        drawing_layout.addWidget(QLabel("画笔工具:"))
        self.shortcut_drawing = QKeySequenceEdit(self.settings.get_shortcut_drawing())
        drawing_layout.addWidget(self.shortcut_drawing)
        shortcut_layout.addLayout(drawing_layout)
        
        # 连接快捷键变更事件
        self.shortcut_start.editingFinished.connect(
            lambda: self._update_shortcut('start'))
        self.shortcut_pause.editingFinished.connect(
            lambda: self._update_shortcut('pause'))
        self.shortcut_stop.editingFinished.connect(
            lambda: self._update_shortcut('stop'))
        self.shortcut_drawing.editingFinished.connect(
            lambda: self._update_shortcut('drawing'))
            
        shortcut_group.setLayout(shortcut_layout)
        return shortcut_group

    def _create_output_settings_group(self):
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        
        # 输出路径设置
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.settings.get_video_path())
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)
        
        browse_button = QToolButton()
        browse_button.setText("...")
        browse_button.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_button)
        
        output_layout.addWidget(QLabel("保存目录:"))
        output_layout.addLayout(path_layout)
        
        output_group.setLayout(output_layout)
        return output_group

    def _create_watermark_mouse_settings_group(self):
        settings_group = QGroupBox("其他设置")
        settings_layout = QVBoxLayout()
        
        # 水印设置按钮
        watermark_btn = QPushButton("设置水印")
        watermark_btn.clicked.connect(self._show_watermark_settings)
        settings_layout.addWidget(watermark_btn)
        
        # 鼠标设置按钮
        mouse_btn = QPushButton("鼠标效果设置")
        mouse_btn.clicked.connect(self._show_mouse_settings)
        settings_layout.addWidget(mouse_btn)
        
        settings_group.setLayout(settings_layout)
        return settings_group 