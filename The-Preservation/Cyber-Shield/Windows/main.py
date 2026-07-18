"""网安智盾 Windows 版 — 程序入口。

装配流程：
    加载配置 → 初始化数据库/加密/监听/录屏/归档/举报 →
    启动 UI 管理器（主窗口 + 配置窗 + 确认弹窗，统一 Tk 根）→
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
from ui.manager import UIManager
from ui.tray import TrayApp


class WangAnZhiDun:
    def __init__(self):
        # 打包/安装后，所有持久文件落在 exe 同级目录（可写）；开发期落在脚本目录
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        self.base = base
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
        self.ui = None
        self._last_trigger = 0
        self._paused = False

        # 本会话统计
        self._c_forensics = 0
        self._c_evidence = 0
        self._c_anti = 0

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

        # 统计 + UI 刷新
        self._c_forensics += 1
        self._c_evidence += len(shots) + (1 if replay else 0)
        self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                          self.kw.match(text) or "命中")
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti)

        # 反伤判定
        anti = self.cfg.anti_strike
        if anti["enabled"] and self.kw.is_attack(text):
            approved = self.ui.ask_confirm(
                app, text, self.cfg.default_clause, anti["confirm_timeout"]
            )
            if approved:
                draft = self.reporter.build_draft(ammo)
                self.reporter.send_email(ammo, draft)
                self._c_anti += 1
                self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti)
                log.info("反伤举报已生成/发送。")
            else:
                log.info("用户放弃反伤。")

        if self.tray:
            self.tray.notify("网安智盾", f"已取证：{app}")

    # ---------- 配置热更新 ----------
    def _apply_config(self, config):
        """配置窗保存后调用，热更新各模块，无需重启。"""
        self.kw.reload(config.keywords)

        rec = config.recorder
        self.recorder.reconfigure(
            enabled=rec["enabled"], fps=rec["fps"],
            buffer_seconds=rec["buffer_seconds"],
            scale=rec["scale"], monitor_index=rec["monitor_index"],
        )

        self.screenshotter.save_dir = config.save_path
        self.screenshotter.fmt = config.screenshot_format.lower()
        self.screenshotter.max_count = config.max_screenshots

        self.archiver.root = config.save_path
        self.archiver.encrypt = config.encrypt
        self.archiver.default_clause = config.default_clause

        self.reporter.email_cfg = config.email

        if self.ui:
            self.ui.set_rec_enabled(rec["enabled"])
        log.info("配置已热更新。")

    # ---------- 交互动作 ----------
    def _toggle_monitor(self):
        self._paused = not self._paused
        if self.monitor:
            if self._paused:
                self.monitor.stop()
            else:
                self.monitor.start()
        running = not self._paused
        if self.ui:
            self.ui.set_running(running)
        if self.tray:
            self.tray.set_running(running)
        log.info("监听已" + ("恢复" if running else "暂停"))

    def _open_evidence(self):
        path = self.cfg.save_path
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            log.warning(f"打开证据目录失败：{e}")

    def _hide_ui(self):
        if self.ui:
            self.ui.hide()

    def _test_trigger(self):
        """模拟一次取证，验证截图/录屏/归档链路（不触发反伤确认）。"""
        def _run():
            self._on_trigger(
                "测试",
                "测试：这是一条模拟的普通通知，用于验证取证链路（截图/录屏/归档）。",
                time.time(),
            )
        threading.Thread(target=_run, daemon=True).start()

    def _refresh_state(self):
        return (
            self.db.recent_events(50),
            (self._c_forensics, self._c_evidence, self._c_anti),
        )

    # ---------- 生命周期 ----------
    def start(self, start_minimized: bool = False):
        # UI 管理器（统一 Tk 根，独立 UI 线程）先建实例，避免监听线程
        # 在 UI 就绪前触发时 self.ui 为 None
        self.ui = UIManager({
            "on_settings": lambda: self.ui.open_config(self.cfg, self._apply_config),
            "on_open_evidence": self._open_evidence,
            "on_toggle": self._toggle_monitor,
            "on_test": self._test_trigger,
            "on_quit": self.stop,
            "on_close": self._hide_ui,
            "on_refresh": self._refresh_state,
        }, start_minimized=start_minimized)

        # 启动自带循环缓冲录屏（不依赖任何外部应用）
        self.recorder.start()

        self.monitor = NotificationMonitor(self.kw, self._on_trigger)
        self.monitor.start()

        self.ui.start()
        self.ui.set_rec_enabled(self.cfg.recorder["enabled"])
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti)

        # 系统托盘
        self.tray = TrayApp(
            evidence_dir=self.cfg.save_path,
            ui=self.ui,
            on_settings=lambda: self.ui.open_config(self.cfg, self._apply_config),
            on_open_evidence=self._open_evidence,
            on_toggle=self._toggle_monitor,
            on_quit=self.stop,
        )
        self.tray.start()
        log.info("网安智盾已启动。")

    def stop(self):
        if self.monitor:
            self.monitor.stop()
        self.recorder.stop()
        self.db.close()
        log.info("网安智盾已退出。")
        os._exit(0)


def main():
    # 开机自启：安装向导写入的 Run 项带 --minimized，启动即最小化到托盘
    start_minimized = any(
        a in ("--minimized", "--startup", "-m") for a in sys.argv[1:]
    )
    app = WangAnZhiDun()
    try:
        app.start(start_minimized=start_minimized)
        # 保持主线程存活
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
