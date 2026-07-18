"""录屏模块：自带循环缓冲录像，无需安装 OBS 等任何第三方应用。

原理：后台线程持续抓取屏幕帧，编码为 JPEG 存入内存环形缓冲
（容量 = fps × 缓冲秒数）。命中关键词时把最近 N 秒帧编码为 MP4 证据。

依赖仅为 opencv-python-headless + mss + numpy（均随 exe 打包，
不依赖任何外部应用）。这取代了原先对 OBS Studio 的依赖。
"""
import os
import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional

import cv2
import mss
import numpy as np


class ScreenRecorder:
    """自带循环缓冲的屏幕录像器。"""

    def __init__(self, fps: int = 10, buffer_seconds: int = 30,
                 scale: float = 0.75, monitor_index: int = 1,
                 enabled: bool = True):
        self.fps = fps
        self.buffer_seconds = buffer_seconds
        self.scale = scale
        self.monitor_index = monitor_index
        self.enabled = enabled
        self.max_frames = max(1, int(fps * buffer_seconds))
        self._buf: deque = deque(maxlen=self.max_frames)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._frame_interval = 1.0 / fps
        self._frame_size = None  # (w, h)

    def start(self):
        if not self.enabled or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _grab_frame(self):
        with mss.mss() as sct:
            idx = self.monitor_index
            if idx < 1 or idx >= len(sct.monitors):
                idx = 1
            shot = sct.grab(sct.monitors[idx])
            img = np.array(shot)  # BGRA
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            if self.scale != 1.0:
                h, w = img.shape[:2]
                img = cv2.resize(img, (int(w * self.scale), int(h * self.scale)))
            return img

    def _loop(self):
        while self._running:
            try:
                t0 = time.time()
                frame = self._grab_frame()
                ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    with self._lock:
                        if self._frame_size is None:
                            self._frame_size = (frame.shape[1], frame.shape[0])
                        self._buf.append(jpg.tobytes())
                dt = time.time() - t0
                if dt < self._frame_interval:
                    time.sleep(self._frame_interval - dt)
            except Exception as e:
                from .logger import log
                log.debug(f"录屏抓帧异常：{e}")
                time.sleep(self._frame_interval)

    def save_buffer(self, out_path: str) -> Optional[str]:
        """把最近 N 秒缓冲编码为 MP4，返回路径；失败降级为 JPEG 目录。"""
        if not self.enabled:
            return None
        with self._lock:
            frames = list(self._buf)
        if not frames or self._frame_size is None:
            return None
        # 优先输出 MP4
        try:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            vw = cv2.VideoWriter(out_path, fourcc, self.fps, self._frame_size)
            for jpg_bytes in frames:
                arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    vw.write(img)
            vw.release()
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return out_path
        except Exception as e:
            from .logger import log
            log.warning(f"MP4 编码失败，降级保存 JPEG 序列：{e}")

        # 降级：保存为按帧编号的 JPEG 目录
        try:
            out_dir = out_path + "_frames"
            os.makedirs(out_dir, exist_ok=True)
            for i, jpg_bytes in enumerate(frames, 1):
                with open(os.path.join(out_dir, f"frame_{i:04d}.jpg"), "wb") as f:
                    f.write(jpg_bytes)
            return out_dir
        except Exception as e:
            from .logger import log
            log.warning(f"JPEG 序列保存也失败：{e}")
            return None

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
