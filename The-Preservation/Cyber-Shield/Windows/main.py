"""网安智盾 WangAnZhiDun — PC 端主入口。

存护命途 · 防打号 / 防点号 / 反伤
红线：仅对恶意攻击取证与反制；不伪造证据；不自动举报。
"""
import os
import sys
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _early_msgbox(title: str, message: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


class WangAnZhiDun:
    def __init__(self, **deps):
        self._ = deps

        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        self.base = base

        self.cfg = self._["ConfigManager"](os.path.join(base, "config.ini"))
        self.db = self._["Database"](os.path.join(base, "wanganzhidun.db"))
        self.crypto = self._["EvidenceCrypto"](base)
        self.kw = self._["KeywordEngine"](self.cfg.keywords)

        self.evidence = self._["EvidenceManager"](self.cfg.save_path, self.cfg)
        self.evidence.set_crypto(self.crypto)

        self.channels = self._["ChannelManager"](self.cfg, self.crypto)
        self.cwas = self._["CWASClient"](
            endpoint=self.cfg.cwas.get("endpoint", ""),
            api_key=self.cfg.cwas.get("api_key", ""),
            enabled=self.cfg.cwas.get("enabled", False),
        )
        self.bus = self._["CoordinationBus"]()

        self.anti_report = self._["AntiReport"]()
        self.anti_tag = self._["AntiTag"](self.cfg.anti_tag)
        self.anti_tag.set_on_freeze(lambda: self._freeze_entries())

        self.monitor = None
        self.tray = None
        self.ui = None

        self._last_trigger = 0
        self._paused = False
        self._start_ts = time.time()

        self._c_forensics = 0
        self._c_evidence = 0
        self._c_anti = 0
        self._c_anti_tag = 0

        self._log = self._["log"]

    def _on_trigger(self, app: str, text: str, ts: float):
        if ts - self._last_trigger < self.cfg.cooldown:
            return
        self._last_trigger = ts

        self._log.info(f"取证触发：{app} | {text[:50]}")

        # --- 防打号检测 ---
        if self.anti_report.is_report_notification(app, text):
            self._log.warning(f"检测到举报反馈通知：{app}")
            self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                              "举报反馈检测", kind="report")
            if self.anti_report.is_malicious_report_chain():
                self._log.warning("检测到恶意聚众举报！")
                self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                                  "恶意聚众举报", kind="report")

        # --- 取证 ---
        if self.cfg.capture_delay > 0:
            time.sleep(self.cfg.capture_delay)

        attachments = self.evidence.collect(app, text, delay=0)

        # --- 标准弹药 ---
        import json
        from core.ammo import StandardAmmo
        ammo = StandardAmmo(
            ammo_type="personal",
            target_account=app,
            target_platform="通知来源",
            violation_time=datetime.now().isoformat(),
            violation_content=text,
            clause=self.cfg.default_clause,
            source_app=app,
        )
        ammo.set_evidence(
            screenshots=attachments.get("screenshots", []),
            replay=attachments.get("replay"),
            raw_text=attachments.get("raw_text"),
        )

        event_id = self.db.add_event(app, self.kw.match(text) or "命中",
                                     self.cfg.save_path, event_type="forensics")
        self.db.add_evidence(event_id, json.dumps(ammo.to_dict(), ensure_ascii=False),
                             str(attachments), self.cfg.default_clause)

        self._c_forensics += 1
        self._c_evidence += len(attachments.get("screenshots", [])) + (1 if attachments.get("replay") else 0)
        self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                          self.kw.match(text) or "命中", kind="forensics")
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti, self._c_anti_tag)

        # --- 反伤 ---
        anti = self.cfg.anti_strike
        if anti.get("enabled") and self.kw.is_attack(text):
            evidence_files = list(attachments.get("screenshots", []))
            if attachments.get("replay"):
                evidence_files.append(attachments["replay"])
            approved, clause = self.ui.ask_confirm(
                app, text, self.cfg.default_clause,
                anti.get("confirm_timeout", 30),
                evidence_files=evidence_files,
                target_account="",
                event_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            if approved:
                ammo.clause = clause
                draft = ammo.to_draft_text()
                draft_path = os.path.join(self.cfg.save_path,
                                          f"report_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                with open(draft_path, "w", encoding="utf-8") as f:
                    f.write(draft)

                report_cfg = self.cfg.channels
                if report_cfg.get("copy_ammo"):
                    try:
                        if self.ui:
                            self.ui.copy_text(draft)
                    except Exception:
                        pass

                results = self.channels.dispatch_with_fallback(ammo, draft_path)
                for ch_name, ok, note in results:
                    self.db.log_counterstrike(event_id, ch_name, ok, note)

                self.bus.notify_counterstrike(ammo.to_dict())

                self._c_anti += 1
                self.ui.add_event(datetime.now().strftime("%H:%M:%S"), app,
                                  "反伤已发起", kind="anti")
                self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti, self._c_anti_tag)
                summary = "，".join(f"{n}{'✓' if ok else '✗'}" for n, ok, _ in results)
                self._log.info(f"反伤结果：{summary}")
                if self.tray:
                    self.tray.notify("网安智盾 · 反伤", f"已并发发起举报：{summary}")
            else:
                self._log.info("用户放弃反伤")

        if self.tray:
            self.tray.notify("网安智盾", f"已取证：{app}")

    def _on_anti_tag_alert(self, alerts: list):
        for event_type, msg in alerts:
            self._c_anti_tag += 1
            self.ui.add_event(datetime.now().strftime("%H:%M:%S"), "防点号",
                              msg, kind="anti_tag")
            self.db.log_anti_tag(event_type, 0, 0, "alert")
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti, self._c_anti_tag)

    def _freeze_entries(self):
        self._log.warning("触发入口自动冻结")
        if self.tray:
            self.tray.notify("网安智盾 · 防点号", "检测到异常频率，已自动冻结入口")

    def _anti_tag_loop(self):
        while True:
            time.sleep(30)
            try:
                alerts = self.anti_tag.check_all()
                if alerts:
                    self._on_anti_tag_alert(alerts)
            except Exception:
                pass

    def _apply_config(self, config):
        self.kw.reload(config.keywords)
        if self.ui:
            self.ui.set_rec_enabled(config.enable_recording)
        self._log.info("配置已热更新")

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
        self._log.info("监听已" + ("恢复" if running else "暂停"))

    def _open_evidence(self):
        self._open_dir(self.cfg.save_path)

    def _view_reports(self):
        self._open_dir(os.path.join(self.base, "reports"))

    def _open_dir(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            self._log.warning(f"打开目录失败：{e}")

    def _show_about(self):
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showinfo(
                "关于网安智盾",
                "网安智盾 WangAnZhiDun · v1.5 测试版\n"
                "存护命途 · 防打号 / 防点号 / 反伤\n\n"
                "个人防御型取证工具：仅记录针对本人的恶意攻击。\n\n"
                "功能：防打号检测、防点号频率监控、多屏截图、\n"
                "OBS 录屏对接、标准弹药 v1 格式、多通道并发举报、\n"
                "CWAS 协同接口。\n\n"
                "红线：不伪造证据、不自动举报、不向非恶意目标使用。",
            )
            r.destroy()
        except Exception:
            pass

    def _reload_config(self):
        try:
            from core.config import ConfigManager
            self.cfg = ConfigManager(self.cfg.path)
            self._apply_config(self.cfg)
            if self.tray:
                self.tray.notify("网安智盾", "配置已重载")
        except Exception as e:
            self._log.warning(f"重载配置失败：{e}")

    def _hide_ui(self):
        if self.ui:
            self.ui.hide()

    def _test_trigger(self):
        def _run():
            self._on_trigger(
                "测试",
                "测试：模拟的恶意通知，用于验证取证链路。",
                time.time(),
            )
        threading.Thread(target=_run, daemon=True).start()

    def _refresh_state(self):
        return (
            self.db.recent_events(50),
            (self._c_forensics, self._c_evidence, self._c_anti),
        )

    def _uptime_loop(self):
        while True:
            time.sleep(30)
            try:
                if self.ui:
                    self.ui.set_uptime(int(time.time() - self._start_ts))
            except Exception:
                pass

    def start(self, start_minimized: bool = False):
        UIManager = self._["UIManager"]
        NotificationMonitor = self._["NotificationMonitor"]
        TrayApp = self._["TrayApp"]

        self.ui = UIManager({
            "on_settings": lambda: self.ui.open_config(self.cfg, self._apply_config),
            "on_open_evidence": self._open_evidence,
            "on_view_db": self._view_reports,
            "on_about": self._show_about,
            "on_toggle": self._toggle_monitor,
            "on_test": self._test_trigger,
            "on_quit": self.stop,
            "on_close": self._hide_ui,
            "on_refresh": self._refresh_state,
        }, start_minimized=start_minimized)

        self.monitor = NotificationMonitor(self.kw, self._on_trigger)
        self.monitor.start()

        self.ui.start()
        self.ui.set_rec_enabled(self.cfg.enable_recording)
        self.ui.set_obs_enabled(self.cfg.obs.get("enabled", False))
        self.ui.set_enc_enabled(self.cfg.encrypt)
        self.ui.set_stats(self._c_forensics, self._c_evidence, self._c_anti, self._c_anti_tag)
        self.ui.set_uptime(0)

        self.tray = TrayApp(
            evidence_dir=self.cfg.save_path,
            ui=self.ui,
            on_settings=lambda: self.ui.open_config(self.cfg, self._apply_config),
            on_open_evidence=self._open_evidence,
            on_test=self._test_trigger,
            on_about=self._show_about,
            on_reload=self._reload_config,
            on_toggle=self._toggle_monitor,
            on_quit=self.stop,
        )
        self.tray.start()

        # --- CWAS ---
        self.cwas.register()
        self._log.info("CWAS 注册完成")

        # --- 防点号循环 ---
        threading.Thread(target=self._anti_tag_loop, daemon=True).start()

        # --- 运行时长 ---
        threading.Thread(target=self._uptime_loop, daemon=True).start()

        self._log.info("网安智盾已启动")

    def stop(self):
        if self.monitor:
            self.monitor.stop()
        self.db.close()
        self._log.info("网安智盾已退出")
        os._exit(0)


def _fatal_error(e: Exception):
    import traceback
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
    popped = False
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
        popped = True
    except Exception:
        pass
    if not popped:
        _early_msgbox("网安智盾 · 启动失败",
                       f"程序无法启动：{e}\n\n详情见 wangzhidun_crash.log")


def main():
    try:
        from core.config import ConfigManager
        from core.logger import log
        from core.keyword_engine import KeywordEngine
        from core.crypto import EvidenceCrypto
        from core.monitor import NotificationMonitor
        from core.evidence import EvidenceManager
        from core.channels import ChannelManager
        from core.ammo import StandardAmmo
        from core.anti_report import AntiReport
        from core.anti_tag import AntiTag
        from core.coordination import CWASClient, CoordinationBus
        from db.database import Database
        from ui.manager import UIManager
        from ui.tray import TrayApp
    except ImportError as e:
        _early_msgbox("网安智盾 · 模块加载失败",
                       f"无法加载必要模块：{e}\n请重新下载或重新构建。")
        raise

    start_minimized = any(a in ("--minimized", "--startup", "-m") for a in sys.argv[1:])
    debug = any(a == "--debug" for a in sys.argv[1:])
    if debug:
        import logging
        from core.logger import setup_logger
        setup_logger(level=logging.DEBUG)

    app = WangAnZhiDun(
        ConfigManager=ConfigManager, KeywordEngine=KeywordEngine,
        EvidenceCrypto=EvidenceCrypto, NotificationMonitor=NotificationMonitor,
        EvidenceManager=EvidenceManager, ChannelManager=ChannelManager,
        AntiReport=AntiReport, AntiTag=AntiTag,
        CWASClient=CWASClient, CoordinationBus=CoordinationBus,
        log=log, Database=Database, UIManager=UIManager, TrayApp=TrayApp,
    )
    try:
        app.start(start_minimized=start_minimized)
    except Exception as e:
        _fatal_error(e)
        return
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
