"""网安智盾 Windows 版 — 程序入口。

装配流程：
    加载配置 → 初始化数据库/加密/监听/录屏/归档/举报 →
    启动托盘 → 进入监听循环（命中关键词 → 截图+录像 → 归档标准弹药 →
    记录 SQLite → 反伤确认弹窗 → 生成举报草稿/邮件）

红线：仅对恶意攻击取证与反制；不伪造证据；不自动举报（需用户确认）。
"""
import os
import sys
import time
import threading
from datetime import datetime

# 让脚本可直接运行（开发期从 Windows/ 目录启动）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import ConfigManager, KeywordEngine, EvidenceCrypto, log
from core.monitor import NotificationMonitor
from core.screenshot import Screenshotter
from core.recorder import ScreenRecorder
from core.archiver import Archiver
from core.reporter import Reporter
from db.database import Database
from ui.tray import TrayApp
from ui.config_window import ConfigWindow
from ui.confirm_dialog import ConfirmDialog


class WangAnZhiDun:
    def __init__(self):
        # 打包/安装后，所有持久文件落在 exe 同级目录（可写）；开发期落在脚本目录
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        self.cfg = ConfigManager(os.path.join(base, "config.ini"))
        self.db = Database(os.path.join(base, "wanganzhidun.db"))
        self.crypto = EvidenceCrypto(base)
        self.kw = KeywordEngine(self.cfg.keywords)

        self.screenshotter = Screenshotter(
            self.cfg.save_path, self.cfg.screenshot_format, self.cfg.max_screenshots
        )
        self.recorder = ScreenRecorder(**self.cfg.recorder)
        self.archiver = Archiver(
            self.cfg.save_path, self.cfg.encrypt, self.crypto, self.cfg.default_clause
        )
        self.reporter = Reporter(self.cfg.email, os.path.join(base, "reports"))

        self.monitor = None
        self.tray = None
        self._last_trigger = 0
        self._paused = False

    # ---------- 核心：命中处理 ----------
    def _on_trigger(self, app: str, text: str, ts: float):
        # 冷却去重
        if ts - self._last_trigger < self.cfg.cooldown:
            return
        self._last_trigger = ts

        log.info(f"取证触发：{app} | {text[:30]}")

        # 延迟截取，等待恶意内容完整显示
        if self.cfg.capture_delay > 0:
            time.sleep(self.cfg.capture_delay)

        shots = self.screenshotter.capture(prefix="shot") if self.cfg.enable_screenshot else []

        replay = None
        if self.cfg.enable_recording and self.recorder.enabled:
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            replay_path = os.path.join(self.cfg.save_path, f"replay_{ts_str}.mp4")
            replay = self.recorder.save_buffer(replay_path)

        # 归档为标准弹药
        ammo = self.archiver.archive(app, text, shots, replay)
        event_id = self.db.add_event(app, self.kw.match(text) or "命中", self.cfg.save_path)
        self.db.add_evidence(event_id, ammo)

        # 反伤判定
        anti = self.cfg.anti_strike
        if anti["enabled"] and self.kw.is_attack(text):
            approved = ConfirmDialog.ask(
                app, text, self.cfg.default_clause, anti["confirm_timeout"]
            )
            if approved:
                draft = self.reporter.build_draft(ammo)
                self.reporter.send_email(ammo, draft)
                log.info("反伤举报已生成/发送。")
            else:
                log.info("用户放弃反伤。")

        if self.tray:
            self.tray.notify("网安智盾", f"已取证：{app}")

    # ---------- 生命周期 ----------
    def start(self):
        # 启动自带循环缓冲录屏（不依赖任何外部应用）
        self.recorder.start()

        self.monitor = NotificationMonitor(self.kw, self._on_trigger)
        self.monitor.start()

        self.tray = TrayApp(
            self.cfg.save_path,
            on_settings=self._open_settings,
            on_toggle=self._toggle,
            on_quit=self.stop,
        )
        self.tray.start()
        log.info("网安智盾已启动。")

    def _open_settings(self):
        ConfigWindow(self.cfg).run()

    def _toggle(self, running: bool):
        self._paused = not running
        if self.monitor:
            if running:
                self.monitor.start()
            else:
                self.monitor.stop()
        log.info("监听已" + ("恢复" if running else "暂停"))

    def stop(self):
        if self.monitor:
            self.monitor.stop()
        self.recorder.stop()
        self.db.close()
        log.info("网安智盾已退出。")
        os._exit(0)


def main():
    app = WangAnZhiDun()
    try:
        app.start()
        # 保持主线程存活
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
