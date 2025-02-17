from PySide6.QtCore import QSettings
import os
from datetime import datetime

class Settings:
    def __init__(self):
        self.settings = QSettings("ScreenRecorder", "Settings")
        
    def get_countdown(self):
        return self.settings.value("countdown_seconds", 3, type=int)
    
    def set_countdown(self, seconds):
        self.settings.setValue("countdown_seconds", seconds)
        
    def get_auto_hide(self):
        return self.settings.value("auto_hide", True, type=bool)
    
    def set_auto_hide(self, auto_hide):
        self.settings.setValue("auto_hide", auto_hide)
    
    def get_shortcut_start(self):
        return self.settings.value("shortcut_start", "Ctrl+R")
    
    def set_shortcut_start(self, shortcut):
        self.settings.setValue("shortcut_start", shortcut)
    
    def get_shortcut_pause(self):
        return self.settings.value("shortcut_pause", "Ctrl+P")
    
    def set_shortcut_pause(self, shortcut):
        self.settings.setValue("shortcut_pause", shortcut)
    
    def get_shortcut_stop(self):
        return self.settings.value("shortcut_stop", "Ctrl+S")
    
    def set_shortcut_stop(self, shortcut):
        self.settings.setValue("shortcut_stop", shortcut)
    
    def get_video_path(self):
        default_path = os.path.join(os.path.expanduser("~"), "Videos", "ScreenRecords")
        path = self.settings.value("video_path", default_path)
        if not os.path.exists(path):
            os.makedirs(path)
        return path
    
    def set_video_path(self, path):
        self.settings.setValue("video_path", path)
    
    def generate_filename(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S") + ".mp4"
    
    def get_shortcut_drawing(self):
        return self.settings.value('shortcut_drawing', 'Ctrl+D')
        
    def set_shortcut_drawing(self, sequence):
        self.settings.setValue('shortcut_drawing', sequence) 