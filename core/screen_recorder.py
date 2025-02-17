import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, QSettings
import cv2
import mss
import threading
import time
import sounddevice as sd
import soundfile as sf
import tempfile
import os
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip
from PySide6.QtGui import QColor, QCursor
import win32api
import winsound
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import butter, lfilter
import noisereduce as nr

class ScreenRecorder(QObject):
    recording_finished = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.recording = False
        self.paused = False
        self.output_file = None
        self.fps = 30
        self.frame_size = (1920, 1080)
        self.temp_video = None
        self.temp_audio = None
        self.audio_source = "系统声音 + 麦克风"
        self.system_volume = 100
        self.mic_volume = 100
        
        # 音频降噪设置
        self.noise_reduction_enabled = False
        self.noise_reduction_strength = 0.5  # 降噪强度 0.0-1.0
        
    def start_recording(self, region=None, output_file="output.mp4"):
        self.recording = True
        self.paused = False
        self.output_file = output_file
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        self.temp_video = os.path.join(temp_dir, "temp_video.mp4")
        self.temp_audio = os.path.join(temp_dir, "temp_audio.wav")
        
        # 使用 MJPG 编码器代替 H264
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.writer = cv2.VideoWriter(
            self.temp_video.replace('.mp4', '.avi'),  # 临时使用 AVI 格式
            fourcc, 
            self.fps,
            self.frame_size,
            isColor=True
        )
        
        # 开始录制线程
        self.record_thread = threading.Thread(target=self._record_screen, args=(region,))
        self.audio_thread = threading.Thread(target=self._record_audio)
        
        self.record_thread.start()
        self.audio_thread.start()
        
    def _record_screen(self, region=None):
        settings = QSettings("ScreenRecorder", "Watermark")
        
        # 加载水印设置
        text = settings.value("text", "")
        text_size = int(settings.value("size", 24))
        
        # 修改透明度值的处理
        opacity = settings.value("opacity", 0.5)  # 默认值改为浮点数
        try:
            # 尝试将字符串转换为浮点数
            opacity = float(opacity)
        except (ValueError, TypeError):
            opacity = 0.5  # 如果转换失败，使用默认值
            
        # 将 0-1 的浮点数转换为 0-255 的整数（用于 OpenCV）
        text_opacity = int(opacity * 255)
        
        image_path = settings.value("image_path", "")
        position = settings.value("position", "右下")
        
        # 加载水印图片
        watermark_image = None
        if image_path and os.path.exists(image_path):
            watermark_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if watermark_image is not None:
                # 调整图片大小
                h, w = watermark_image.shape[:2]
                new_h = int(self.frame_size[1] * 0.2)  # 设置为视频高度的 20%
                new_w = int(w * new_h / h)
                watermark_image = cv2.resize(watermark_image, (new_w, new_h))
                
                # 处理图片透明度
                if watermark_image.shape[2] == 4:  # 如果有 alpha 通道
                    alpha = watermark_image[:, :, 3] * opacity  # 应用透明度设置
                    watermark_image[:, :, 3] = alpha
                else:
                    # 如果没有 alpha 通道，创建一个
                    alpha = np.ones((new_h, new_w)) * 255 * opacity
                    watermark_image = cv2.cvtColor(watermark_image, cv2.COLOR_BGR2BGRA)
                    watermark_image[:, :, 3] = alpha
        
        # 加载鼠标设置
        mouse_settings = QSettings("ScreenRecorder", "Mouse")
        enable_click = mouse_settings.value("enable_click", True, type=bool)
        click_color = QColor(mouse_settings.value("click_color", "#FF0000"))
        click_size = mouse_settings.value("click_size", 20, type=int)
        enable_sound = mouse_settings.value("enable_sound", True, type=bool)
        
        enable_trail = mouse_settings.value("enable_trail", True, type=bool)
        trail_color = QColor(mouse_settings.value("trail_color", "#0000FF"))
        trail_width = mouse_settings.value("trail_width", 2, type=int)
        
        enable_highlight = mouse_settings.value("enable_highlight", True, type=bool)
        highlight_style = mouse_settings.value("highlight_style", "圆形光环")
        highlight_size = mouse_settings.value("highlight_size", 50, type=int)
        
        # 鼠标轨迹历史
        trail_points = []
        last_mouse_pos = None
        click_effects = []  # 存储点击效果的位置和时间
        
        with mss.mss() as sct:
            # 如果没有指定区域，使用主显示器
            if region is None:
                monitor = sct.monitors[1]  # 主显示器
            else:
                monitor = region
            
            while self.recording:
                if not self.paused:
                    # 捕获屏幕
                    screenshot = sct.grab(monitor)
                    frame = np.array(screenshot)
                    
                    # 转换颜色空间
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    # 调整大小
                    frame = cv2.resize(frame, self.frame_size)
                    
                    # 添加水印
                    if text:
                        # 创建透明层
                        overlay = frame.copy()
                        
                        # 设置字体
                        fontpath = "simhei.ttf"  # 使用系统自带的黑体字体
                        font = ImageFont.truetype(fontpath, text_size)
                        img_pil = Image.fromarray(frame)
                        draw = ImageDraw.Draw(img_pil)
                        
                        # 获取文字大小
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        # 确定位置
                        if position == "左上":
                            pos = (10, 10)
                        elif position == "右上":
                            pos = (frame.shape[1] - text_width - 10, 10)
                        elif position == "左下":
                            pos = (10, frame.shape[0] - text_height - 10)
                        else:  # 右下
                            pos = (frame.shape[1] - text_width - 10, 
                                  frame.shape[0] - text_height - 10)
                        
                        # 绘制文字
                        draw.text(
                            pos, 
                            text,
                            font=font,
                            fill=(255, 255, 255),
                            stroke_width=1,
                            stroke_fill=(0, 0, 0)
                        )
                        
                        # 转换回OpenCV格式
                        frame = np.array(img_pil)
                    
                    if watermark_image is not None:
                        # 添加图片水印
                        h, w = watermark_image.shape[:2]
                        
                        # 确定位置
                        if position == "左上":
                            x, y = 10, 10
                        elif position == "右上":
                            x, y = frame.shape[1] - w - 10, 10
                        elif position == "左下":
                            x, y = 10, frame.shape[0] - h - 10
                        else:  # 右下
                            x, y = frame.shape[1] - w - 10, frame.shape[0] - h - 10
                            
                        # 合并水印
                        roi = frame[y:y+h, x:x+w]
                        if watermark_image.shape[2] == 4:  # 带透明通道
                            alpha = watermark_image[:, :, 3] / 255.0
                            for c in range(3):
                                roi[:, :, c] = (
                                    roi[:, :, c] * (1 - alpha) +
                                    watermark_image[:, :, c] * alpha
                                )
                        else:
                            roi[:] = watermark_image
                    
                    # 获取当前鼠标位置
                    mouse_pos = QCursor.pos()
                    mouse_x = mouse_pos.x() - monitor['left']
                    mouse_y = mouse_pos.y() - monitor['top']
                    
                    # 处理鼠标轨迹
                    if enable_trail:
                        if last_mouse_pos:
                            trail_points.append((last_mouse_pos, (mouse_x, mouse_y)))
                        last_mouse_pos = (mouse_x, mouse_y)
                        
                        # 绘制轨迹
                        for start, end in trail_points[-20:]:  # 只保留最近的20个点
                            cv2.line(frame, start, end, 
                                   (trail_color.blue(), trail_color.green(), trail_color.red()),
                                   trail_width)
                    
                    # 处理鼠标高亮
                    if enable_highlight:
                        if highlight_style == "圆形光环":
                            cv2.circle(frame, (mouse_x, mouse_y), highlight_size,
                                     (255, 255, 255), 2)
                        elif highlight_style == "聚光灯":
                            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                            cv2.circle(mask, (mouse_x, mouse_y), highlight_size, 255, -1)
                            frame = cv2.addWeighted(frame, 0.7, 
                                                  cv2.bitwise_and(frame, frame, mask=mask), 0.3, 0)
                        elif highlight_style == "波纹":
                            for i in range(3):
                                size = highlight_size - i * 10
                                if size > 0:
                                    cv2.circle(frame, (mouse_x, mouse_y), size,
                                             (255, 255, 255), 1)
                    
                    # 处理点击效果
                    if enable_click:
                        buttons = win32api.GetKeyState(0x01)  # 检查鼠标左键状态
                        if buttons < 0:  # 鼠标按下
                            click_effects.append({
                                'pos': (mouse_x, mouse_y),
                                'time': time.time(),
                                'size': 0
                            })
                            if enable_sound:
                                winsound.PlaySound("click.wav", winsound.SND_ASYNC)
                        
                        # 更新和绘制点击效果
                        current_time = time.time()
                        new_effects = []
                        for effect in click_effects:
                            if current_time - effect['time'] < 0.5:  # 效果持续0.5秒
                                effect['size'] = min(effect['size'] + 2, click_size)
                                cv2.circle(frame, effect['pos'], effect['size'],
                                         (click_color.blue(), click_color.green(), click_color.red()),
                                         2)
                                new_effects.append(effect)
                        click_effects = new_effects
                    
                    # 写入帧
                    self.writer.write(frame)
                    
                    # 控制帧率
                    time.sleep(1/self.fps)
        
        self.writer.release()
        
    def _record_audio(self):
        # 设置音频参数
        sample_rate = 44100
        channels = 2
        chunk_size = 4096  # 增加缓冲区大小
        
        # 根据音频源设置选择录制方式
        record_system = self.audio_source in ["系统声音 + 麦克风", "仅系统声音"]
        record_mic = self.audio_source in ["系统声音 + 麦克风", "仅麦克风声音"]
        
        if self.audio_source == "静音":
            # 创建静音文件
            duration = 1  # 临时duration，后面会根据视频长度调整
            samples = np.zeros((int(duration * sample_rate), channels), dtype=np.float32)
            sf.write(self.temp_audio, samples, sample_rate)
            return
            
        try:
            with sf.SoundFile(self.temp_audio, mode='w', samplerate=sample_rate,
                            channels=channels) as audio_file:
                
                # 设置输入流
                streams = []
                if record_system:
                    try:
                        # 获取系统声音设备
                        devices = sd.query_devices()
                        wasapi_devices = [
                            i for i, d in enumerate(devices)
                            if 'WASAPI' in d['name'] and d['max_input_channels'] > 0
                        ]
                        if wasapi_devices:
                            system_stream = sd.InputStream(
                                samplerate=sample_rate,
                                channels=channels,
                                device=wasapi_devices[0]
                            )
                            streams.append(system_stream)
                    except Exception as e:
                        print(f"系统声音录制初始化失败: {e}")
                
                if record_mic:
                    try:
                        mic_stream = sd.InputStream(
                            samplerate=sample_rate,
                            channels=channels,
                            device=None  # 使用默认输入设备
                        )
                        streams.append(mic_stream)
                    except Exception as e:
                        print(f"麦克风录制初始化失败: {e}")
                
                # 开始录制
                for stream in streams:
                    stream.start()
                
                while self.recording:
                    if not self.paused:
                        # 使用更大的缓冲区
                        mixed_audio = np.zeros((chunk_size, channels), dtype=np.float32)
                        
                        for i, stream in enumerate(streams):
                            try:
                                data, _ = stream.read(chunk_size)
                                volume = (self.system_volume if i == 0 else self.mic_volume) / 100
                                mixed_audio += data * volume
                            except Exception as e:
                                print(f"音频录制错误: {e}")
                                continue
                        
                        # 在录制音频时应用降噪
                        if self.audio_source != "静音" and self.noise_reduction_enabled:
                            try:
                                mixed_audio = self._process_audio(mixed_audio, sample_rate)
                            except Exception as e:
                                print(f"降噪处理错误: {e}")
                        
                        audio_file.write(mixed_audio)
                
                # 停止所有流
                for stream in streams:
                    stream.stop()
                    stream.close()
                    
        except Exception as e:
            print(f"音频录制错误: {e}")
            # 创建静音文件作为后备
            duration = 1
            samples = np.zeros((int(duration * sample_rate), channels), dtype=np.float32)
            sf.write(self.temp_audio, samples, sample_rate)
        
    def _process_audio(self, audio_data, sample_rate):
        if not self.noise_reduction_enabled:
            return audio_data
            
        # 确保音频数据足够长
        if len(audio_data) < 2048:
            return audio_data
            
        try:
            # 将音频数据转换为float32类型
            audio_float = audio_data.astype(np.float32)
            
            # 1. 语音增强的带通滤波
            nyquist = sample_rate / 2
            # 人声频率范围：300Hz - 3400Hz
            low_cutoff = 300 / nyquist
            high_cutoff = 3400 / nyquist
            
            # 创建巴特沃斯带通滤波器
            b, a = butter(6, [low_cutoff, high_cutoff], btype='band')
            
            # 2. 对每个通道分别处理
            enhanced_audio = np.zeros_like(audio_float)
            for channel in range(audio_float.shape[1]):
                # 应用带通滤波
                channel_data = lfilter(b, a, audio_float[:, channel])
                
                # 计算信号能量
                frame_length = 512
                hop_length = frame_length // 4
                num_frames = 1 + (len(channel_data) - frame_length) // hop_length
                
                # 使用重叠帧处理
                processed_data = np.zeros_like(channel_data)
                for i in range(num_frames):
                    start = i * hop_length
                    end = start + frame_length
                    
                    # 获取当前帧
                    frame = channel_data[start:end]
                    
                    # 计算帧能量
                    frame_energy = np.mean(frame ** 2)
                    
                    # 自适应阈值
                    noise_threshold = np.sqrt(frame_energy) * 0.1
                    
                    # 非线性抑制
                    gain = 1.0 / (1.0 + np.exp(-(np.abs(frame) - noise_threshold) * 10))
                    processed_frame = frame * gain
                    
                    # 使用重叠相加法
                    if i == 0:
                        processed_data[start:end] = processed_frame
                    else:
                        # 创建渐变窗口
                        fade_in = np.linspace(0, 1, hop_length)
                        fade_out = np.linspace(1, 0, frame_length - hop_length)
                        window = np.concatenate([fade_in, fade_out])
                        
                        # 应用渐变
                        processed_data[start:end] = processed_data[start:end] * (1 - window) + \
                                                  processed_frame * window
                
                # 应用降噪强度
                strength = self.noise_reduction_strength * 0.8  # 降低最大强度以保持自然
                enhanced_audio[:, channel] = channel_data * (1 - strength) + processed_data * strength
            
            # 3. 动态范围压缩
            compressed = np.zeros_like(enhanced_audio)
            for channel in range(enhanced_audio.shape[1]):
                data = enhanced_audio[:, channel]
                
                # 计算RMS能量
                rms = np.sqrt(np.mean(data ** 2))
                
                # 自适应压缩阈值
                threshold = rms * 1.5
                
                # 软膝压缩
                ratio = 2.0
                knee_width = threshold * 0.3
                
                # 计算增益
                gain = np.ones_like(data)
                magnitude = np.abs(data)
                
                # 软膝区域
                knee_mask = (magnitude > (threshold - knee_width)) & (magnitude < (threshold + knee_width))
                above_mask = magnitude >= (threshold + knee_width)
                
                # 软膝压缩
                knee_gain = 1.0 - (1.0 - 1.0/ratio) * ((magnitude[knee_mask] - (threshold - knee_width)) / (2 * knee_width)) ** 2
                gain[knee_mask] = knee_gain
                
                # 硬压缩
                gain[above_mask] = (threshold + (magnitude[above_mask] - threshold) / ratio) / magnitude[above_mask]
                
                # 应用增益
                compressed[:, channel] = data * gain
            
            # 4. 最终处理
            # 应用makeup增益
            makeup_gain = 1.2
            compressed *= makeup_gain
            
            # 限幅以防止削波
            compressed = np.clip(compressed, -0.95, 0.95)
            
            # 转换回int16
            return (compressed * 32768.0).astype(np.int16)
            
        except Exception as e:
            print(f"音频降噪处理失败: {e}")
            return audio_data
        
    def _merge_audio_video(self):
        try:
            # 使用 moviepy 合并音频和视频，并转换为 MP4
            video_clip = VideoFileClip(self.temp_video.replace('.mp4', '.avi'))
            audio_clip = AudioFileClip(self.temp_audio)
            
            # 设置输出参数
            final_clip = video_clip.with_audio(audio_clip)
            final_clip.write_videofile(
                self.output_file,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=self.fps,
                threads=4,
                preset='ultrafast',
                ffmpeg_params=[
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p'
                ]
            )
            
            # 清理资源
            video_clip.close()
            audio_clip.close()
            
        except Exception as e:
            print(f"合并音视频失败: {e}")
            # 尝试直接复制视频文件作为备选方案
            import shutil
            try:
                # 转换 AVI 到 MP4
                os.system(f'ffmpeg -i {self.temp_video.replace(".mp4", ".avi")} -c:v libx264 -preset ultrafast {self.output_file}')
            except Exception as copy_error:
                print(f"转换视频文件失败: {copy_error}")
        
        finally:
            # 清理临时文件
            try:
                if os.path.exists(self.temp_video.replace('.mp4', '.avi')):
                    os.remove(self.temp_video.replace('.mp4', '.avi'))
                if os.path.exists(self.temp_audio):
                    os.remove(self.temp_audio)
            except Exception as cleanup_error:
                print(f"清理临时文件失败: {cleanup_error}")
        
    def pause_recording(self):
        self.paused = True
        
    def resume_recording(self):
        self.paused = False
        
    def stop_recording(self):
        if not self.recording:
            return
            
        self.recording = False
        try:
            if hasattr(self, 'record_thread'):
                self.record_thread.join()
                self.audio_thread.join()
                
                # 确保视频写入器正确关闭
                if hasattr(self, 'writer') and self.writer:
                    self.writer.release()
                    
                self._merge_audio_video()
                self.recording_finished.emit(self.output_file)
        except Exception as e:
            print(f"停止录制失败: {e}")

    def _add_watermark(self, frame):
        if self.settings.get_watermark_type() == "text":
            return self._add_text_watermark(frame)
        else:
            return self._add_image_watermark(frame)

    def _add_image_watermark(self, frame):
        image_path = self.settings.get_watermark_image()
        if not image_path or not os.path.exists(image_path):
            return frame
            
        try:
            # 读取水印图片
            watermark = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if watermark is None:
                return frame
                
            # 调整水印大小
            target_width = frame.shape[1] // 4  # 水印宽度为视频宽度的1/4
            aspect_ratio = watermark.shape[1] / watermark.shape[0]
            target_height = int(target_width / aspect_ratio)
            watermark = cv2.resize(watermark, (target_width, target_height))
            
            # 处理透明度
            opacity = self.settings.get_watermark_opacity()
            
            # 如果水印图片有alpha通道
            if watermark.shape[2] == 4:
                alpha = watermark[:, :, 3] / 255.0 * opacity
                alpha = np.expand_dims(alpha, axis=2)
                rgb = watermark[:, :, :3]
            else:
                alpha = np.ones((watermark.shape[0], watermark.shape[1], 1)) * opacity
                rgb = watermark
                
            # 计算位置（右下角）
            y_offset = frame.shape[0] - watermark.shape[0] - 10
            x_offset = frame.shape[1] - watermark.shape[1] - 10
            
            # 创建ROI
            roi = frame[y_offset:y_offset + watermark.shape[0], 
                       x_offset:x_offset + watermark.shape[1]]
                       
            # 混合水印
            blended = roi * (1 - alpha) + rgb * alpha
            frame[y_offset:y_offset + watermark.shape[0], 
                 x_offset:x_offset + watermark.shape[1]] = blended
                 
            return frame
        except Exception as e:
            print(f"添加图片水印失败: {e}")
            return frame 