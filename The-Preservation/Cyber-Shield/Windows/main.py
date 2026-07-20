"""网安智盾 Windows 版 — 程序入口（UI 改进版）。

相对旧版改动（仅接线与少量增强，核心取证/归档/举报逻辑不变）：
    [UI改进-1] start() 的 callbacks 增加 on_view_db / on_about；
                托盘 TrayApp 增加 on_test / on_about / on_reload；
    [UI改进-2] _on_trigger 中 ask_confirm 传入 evidence_files / target_account /
                event_time，启用反伤弹窗「标准弹药预览」与证据缩略图；
                反伤确认后再插入一条 kind="anti" 着色事件；
    [UI改进-3] 新增 _show_about / _reload_config / _view_reports / 运行时长刷新。

红线：仅对恶意攻击取证与反制；不伪造证据；不自动举报（需用户确认）。
"""
import os
import sys
import time
import threading
from datetime import datetime

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
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        self.base = base
        self.cfg_path = os.path.join(base, "config.ini")  # [UI改进] 保存路径供重载
        self.cfg = ConfigManager(self.cfg_path)
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
        self.reporter = Reporter(self.cfg.email, os.path.join(base, "reports"), self.crypto)

        self.monitor = None
        self.tray = None
        self.ui = None
        self._last_trigger = 0
        self._paused = False
        self._start_ts = time.time()  # [UI改进] 运行时长基准

        self._c_forensics = 0
        self._c_evidence = 0
        self._c_anti = 0

    # ---------- 核心：命中处理 ----------
    def _on_trigger(self, app: str, text: str, ts: float):
        if ts - self._last_trigger < self.cfg.cooldown:
            return
        self._last_trigger = ts

        log.info(f"取证触发：{app} | {text[:30]}")

        if self.cfg.capture_delay > 0:
            time.sleep(self.cfg.capture_delay)

        shots = self.screenshotter.capture(prefix="shot") if self.cfg.enable_screenshot else []

        replay = None
        if self.cfg.enable_recording and self.recorder.enabled:
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            replay_path = os.path.join(self.cfg.save_path, f"replay_{ts_str}.mp4")
            replay = self.recorder.save_buffer(replay_path)

        ammo = self.archiver.archive(
            app, text, shots, replay, clause=self.cfg.default_clause
        )
        event_id = self.db.add_event(app, self.kw.match(text) or "命中", self.cfg.save_path)
        self.db.add_evidence(event_id, ammo)

        self._c_forensics += 1
        self._c_evidence += len(shots) + (1 if replay else 0)
        self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                          self.kw.match(text) or "命中", kind="forensics")
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti)

        # 反伤判定
        anti = self.cfg.anti_strike
        if anti["enabled"] and self.kw.is_attack(text):
            evidence_files = list(shots) + ([replay] if replay else [])  # [UI改进]
            approved, clause = self.ui.ask_confirm(
                app, text, self.cfg.default_clause, anti["confirm_timeout"],
                evidence_files=evidence_files,
                target_account="",
                event_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            if approved:
                ammo["clause"] = clause
                self.db.update_evidence_clause(event_id, clause)
                draft = self.reporter.build_draft(ammo)
                report_cfg = self.cfg.report
                if report_cfg.get("copy_ammo") and self.ui:
                    try:
                        with open(draft, "r", encoding="utf-8") as f:
                            self.ui.copy_text(f.read())
                    except Exception:
                        pass
                results = self.reporter.report_channels(ammo, draft, report_cfg)
                self._c_anti += 1
                self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                                  self.kw.match(text) or "命中", kind="anti")  # [UI改进]
                self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti)
                summary = "，".join(f"{n}{'✓' if ok else '✗'}" for n, ok, _ in results)
                log.info(f"反伤并发举报：{summary}")
                if self.tray:
                    self.tray.notify("网安智盾 · 反伤", f"已并发发起举报：{summary}")
            else:
                log.info("用户放弃反伤。")

        if self.tray:
            self.tray.notify("网安智盾", f"已取证：{app}")

    # ---------- 配置热更新 ----------
    def _apply_config(self, config):
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
        self._open_dir(self.cfg.save_path)

    def _view_reports(self):  # [UI改进] 证据库（举报草稿）入口
        self._open_dir(os.path.join(self.base, "reports"))

    def _open_dir(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            log.warning(f"打开目录失败：{e}")

    def _show_about(self):  # [UI改进] 关于
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showinfo(
                "关于网安智盾",
                "网安智盾 WangAnZhiDun · 网安智盾 v0.2.x（UI 改进版）\n"
                "存护命途 · 防打号 / 防点号 / 反伤\n\n"
                "个人防御型取证工具：仅记录针对本人的恶意攻击，证据真实，\n"
                "经官方合规渠道（12377 / 腾讯卫士 / 12321 / 举报邮箱）举报。\n\n"
                "红线：不伪造证据、不自动举报、不向非恶意目标使用。",
            )
            r.destroy()
        except Exception:
            pass

    def _reload_config(self):  # [UI改进] 重载配置
        try:
            self.cfg = ConfigManager(self.cfg_path)
            self._apply_config(self.cfg)
            if self.tray:
                self.tray.notify("网安智盾", "配置已重载并热更新。")
        except Exception as e:
            log.warning(f"重载配置失败：{e}")

    def _hide_ui(self):
        if self.ui:
            self.ui.hide()

    def _test_trigger(self):
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

    def _uptime_loop(self):  # [UI改进] 运行时长刷新
        while True:
            time.sleep(30)
            try:
                if self.ui:
                    self.ui.set_uptime(int(time.time() - self._start_ts))
            except Exception:
                pass

    # ---------- 生命周期 ----------
    def start(self, start_minimized: bool = False):
        self.ui = UIManager({
            "on_settings": lambda: self.ui.open_config(self.cfg, self._apply_config),
            "on_open_evidence": self._open_evidence,
            "on_view_db": self._view_reports,           # [UI改进]
            "on_about": self._show_about,               # [UI改进]
            "on_toggle": self._toggle_monitor,
            "on_test": self._test_trigger,
            "on_quit": self.stop,
            "on_close": self._hide_ui,
            "on_refresh": self._refresh_state,
        }, start_minimized=start_minimized)

        self.recorder.start()
        self.monitor = NotificationMonitor(self.kw, self._on_trigger)
        self.monitor.start()

        self.ui.start()
        self.ui.set_rec_enabled(self.cfg.recorder["enabled"])
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti)
        self.ui.set_uptime(0)

        self.tray = TrayApp(
            evidence_dir=self.cfg.save_path,
            ui=self.ui,
            on_settings=lambda: self.ui.open_config(self.cfg, self._apply_config),
            on_open_evidence=self._open_evidence,
            on_test=self._test_trigger,        # [UI改进]
            on_about=self._show_about,         # [UI改进]
            on_reload=self._reload_config,     # [UI改进]
            on_toggle=self._toggle_monitor,
            on_quit=self.stop,
        )
        self.tray.start()
        threading.Thread(target=self._uptime_loop, daemon=True).start()  # [UI改进]
        log.info("网安智盾已启动。")

    def stop(self):
        if self.monitor:
            self.monitor.stop()
        self.recorder.stop()
        self.db.close()
        log.info("网安智盾已退出。")
        os._exit(0)


def _fatal_error(e: Exception):
    import os
    import traceback
    from datetime import datetime
    tb = traceback.format_exc()
    try:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base = "."
    try:
        with open(os.path.join(base, "wangzhidun_crash.log"),
                  "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] 致命错误:\n{tb}\n")
    except Exception:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(
            "网安智盾 · 启动失败",
            f"程序无法启动：\n{e}\n\n详情见 wangzhidun_crash.log",
        )
        r.destroy()
    except Exception:
        pass


def main():
    start_minimized = any(
        a in ("--minimized", "--startup", "-m") for a in sys.argv[1:]
    )
    app = WangAnZhiDun()
    try:
        app.start(start_minimized=start_minimized)
    except Exception as e:  # noqa: BLE001
        _fatal_error(e)
        return
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
