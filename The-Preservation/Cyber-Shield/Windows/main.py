import os
import sys
import time
import json
import uuid
import queue
import threading
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _early_msgbox(title: str, message: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


# ── IPC helpers ────────────────────────────────────────────

def _send(pipe, msg: dict):
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    if hasattr(pipe, "encoding"):
        pipe.write(line)
    else:
        pipe.write(line.encode("utf-8"))
    pipe.flush()


def _recv(pipe) -> dict:
    line = pipe.readline()
    if not line:
        raise EOFError("pipe closed")
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    return json.loads(line)


_CONFIRM_RESP = {}  # id -> threading.Event
_CONFIRM_RESP_LOCK = threading.Lock()


def _on_confirm_res(msg: dict):
    cid = msg.get("id")
    if not cid:
        return
    with _CONFIRM_RESP_LOCK:
        ev = _CONFIRM_RESP.pop(cid, None)
    if ev:
        ev.data = msg
        ev.set()


# ── UI 进程 ────────────────────────────────────────────────

def _run_ui_process(engine_stdin, engine_stdout, start_minimized: bool):
    """在子进程中运行 UI（tkinter + 托盘），通过 stdin/stdout 与引擎通信。"""

    import logging
    from core.logger import setup_logger as _sl
    _sl(level=logging.DEBUG if "--debug" in sys.argv else logging.INFO)

    from ui.manager import UIManager
    from ui.tray import TrayApp
    from core.config import ConfigManager
    from core.logger import log

    base = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, "frozen", False) else os.path.dirname(sys.executable)

    # 读配置
    cfg_path = os.path.join(base, "config.ini")
    cfg = ConfigManager(cfg_path)
    save_path = cfg.save_path

    # ── 引擎过来的命令分发 ──
    _pending_confirm = {}

    def _engine_listener():
        while True:
            try:
                msg = _recv(engine_stdin)
            except (EOFError, ConnectionError):
                log.info("引擎断开，UI 退出")
                os._exit(0)
                return
            try:
                t = msg.get("type")
                if t == "event":
                    _ui.add_event(msg["time"], msg["source"], msg["keyword"], msg.get("kind", "forensics"))
                elif t == "stats":
                    _ui.set_stats(msg["forensics"], msg["evidence"], msg["anti"], msg.get("anti_tag", 0))
                elif t == "uptime":
                    _ui.set_uptime(msg["seconds"])
                elif t == "running":
                    _ui.set_running(msg["running"])
                elif t == "rec_state":
                    _ui.set_rec_enabled(msg["enabled"])
                elif t == "obs_state":
                    _ui.set_obs_enabled(msg["enabled"])
                elif t == "enc_state":
                    _ui.set_enc_enabled(msg["enabled"])
                elif t == "events_refresh":
                    _ui.refresh_events(msg.get("events", []))
                elif t == "notify":
                    _tray.notify(msg["title"], msg["message"])
                elif t == "confirm_req":
                    _handle_confirm_req(msg)
                elif t == "shutdown":
                    log.info("收到引擎关闭信号")
                    os._exit(0)
            except Exception as e:
                log.warning(f"UI 消息处理异常：{e}")

    def _handle_confirm_req(msg: dict):
        cid = msg["id"]
        dlg = _ui.ask_confirm(
            msg["source"], msg["text"], msg.get("clause", ""),
            msg.get("timeout", 30),
            evidence_files=msg.get("evidence_files"),
            target_account=msg.get("target_account", ""),
            event_time=msg.get("event_time", ""),
        )
        res = {"type": "confirm_res", "id": cid, "approved": dlg[0], "clause": dlg[1]}
        _send(engine_stdout, res)

    # ── 设置窗口：UI 进程直接读写 config.ini ──
    def _open_settings():
        try:
            dlg_cfg = ConfigManager(cfg_path)
            def _on_applied(new_cfg):
                _send(engine_stdout, {"type": "reload"})
            _ui.open_config(dlg_cfg, _on_applied)
        except Exception as e:
            log.warning(f"设置窗口启动失败：{e}")

    def _open_hardening():
        from ui.hardening_dialog import HardeningDialog
        try:
            dlg_cfg = ConfigManager(cfg_path)
            dlg = HardeningDialog(_ui.root, dlg_cfg)
            dlg.show()
        except Exception as e:
            log.warning(f"加固窗口启动失败：{e}")

    # ── UI 回调用户操作 → 发消息给引擎 ──
    callbacks = {
        "on_settings": _open_settings,
        "on_open_evidence": lambda: _send(engine_stdout, {"type": "open_evidence"}),
        "on_view_db": lambda: _send(engine_stdout, {"type": "view_db"}),
        "on_about": lambda: _send(engine_stdout, {"type": "about"}),
        "on_toggle": lambda: _send(engine_stdout, {"type": "toggle"}),
        "on_test": lambda: _send(engine_stdout, {"type": "test"}),
        "on_quit": lambda: _send(engine_stdout, {"type": "shutdown"}),
        "on_close": lambda: _send(engine_stdout, {"type": "hide"}),
    }

    _ui = UIManager(callbacks, start_minimized=start_minimized)
    _tray = TrayApp(
        evidence_dir=save_path,
        ui=_ui,
        on_settings=_open_settings,
        on_hardening=_open_hardening,
        on_open_evidence=lambda: _send(engine_stdout, {"type": "open_evidence"}),
        on_test=lambda: _send(engine_stdout, {"type": "test"}),
        on_about=lambda: _send(engine_stdout, {"type": "about"}),
        on_reload=lambda: _send(engine_stdout, {"type": "reload"}),
        on_toggle=lambda: _send(engine_stdout, {"type": "toggle"}),
        on_quit=lambda: _send(engine_stdout, {"type": "shutdown"}),
    )

    _ui.start()

    from ui.hardening_dialog import show_if_needed as _show_hardening
    _show_hardening(_ui.root, cfg_path)

    _tray.start()
    threading.Thread(target=_engine_listener, daemon=True).start()
    _send(engine_stdout, {"type": "ready"})

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


# ── 引擎 ────────────────────────────────────────────────────

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
        self.kw = self._["KeywordEngine"](self.cfg.keywords, attack_keywords=self.cfg.attack_keywords)

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
        self._ui_proc = None
        self._ui_stdin = None
        self._ui_stdout = None

        self._last_trigger = 0
        self._paused = False
        self._start_ts = time.time()

        self._c_forensics = 0
        self._c_evidence = 0
        self._c_anti = 0
        self._c_anti_tag = 0

        self._log = self._["log"]

    # ── IPC 发送 ──

    def _ui_send(self, msg: dict):
        if self._ui_stdin:
            try:
                _send(self._ui_stdin, msg)
            except Exception:
                pass

    def _ui_listener(self):
        while True:
            try:
                msg = _recv(self._ui_stdout)
            except (EOFError, ConnectionError):
                self._log.warning("UI 进程断开")
                self._restart_ui()
                return
            try:
                t = msg.get("type")
                if t == "ready":
                    self._log.info("UI 已就绪")
                elif t == "confirm_res":
                    _on_confirm_res(msg)
                elif t == "toggle":
                    self._toggle_monitor()
                elif t == "test":
                    self._test_trigger()
                elif t == "about":
                    self._show_about()
                elif t == "open_evidence":
                    self._open_dir(self.cfg.save_path)
                elif t == "view_db":
                    self._open_dir(os.path.join(self.base, "reports"))
                elif t == "reload":
                    self._reload_config()
                elif t == "shutdown":
                    self._log.info("用户退出")
                    self.stop()
                elif t == "hide":
                    pass
            except Exception as e:
                self._log.warning(f"引擎消息处理异常：{e}")

    # ── UI 进程生命周期 ──

    def _start_ui(self, start_minimized: bool = False):
        exe = sys.executable if getattr(sys, "frozen", False) else sys.executable
        script = [] if getattr(sys, "frozen", False) else [__file__]
        args = [exe] + script + ["--ui"]
        if start_minimized:
            args.append("--minimized")
        if "--debug" in sys.argv:
            args.append("--debug")

        self._ui_proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.base,
        )
        self._ui_stdin = self._ui_proc.stdin
        self._ui_stdout = self._ui_proc.stdout

        threading.Thread(target=self._ui_listener, daemon=True).start()

    def _restart_ui(self):
        self._log.warning("重启 UI 进程")
        try:
            if self._ui_proc:
                self._ui_proc.kill()
        except Exception:
            pass
        self._start_ui()
        self._ui_send({"type": "running", "running": not self._paused})
        self._ui_send({"type": "rec_state", "enabled": self.cfg.enable_recording})
        self._ui_send({"type": "obs_state", "enabled": self.cfg.obs.get("enabled", False)})
        self._ui_send({"type": "enc_state", "enabled": self.cfg.encrypt})
        self._ui_send({"type": "stats", "forensics": self._c_forensics, "evidence": self._c_evidence, "anti": self._c_anti, "anti_tag": self._c_anti_tag})

    # ── 引擎逻辑 ──

    def _on_trigger(self, app: str, text: str, ts: float):
        if ts - self._last_trigger < self.cfg.cooldown:
            return
        self._last_trigger = ts
        self._log.info(f"取证触发：{app} | {text[:50]}")

        now = datetime.now()
        ts_str = now.strftime("%H:%M:%S")

        if self.anti_report.is_report_notification(app, text):
            self._log.warning(f"检测到举报反馈通知：{app}")
            self._ui_send({"type": "event", "time": ts_str, "source": app, "keyword": "举报反馈检测", "kind": "report"})
            if self.anti_report.is_malicious_report_chain():
                self._log.warning("检测到恶意聚众举报！")
                self._ui_send({"type": "event", "time": ts_str, "source": app, "keyword": "恶意聚众举报", "kind": "report"})

        if self.cfg.capture_delay > 0:
            time.sleep(self.cfg.capture_delay)

        attachments = self.evidence.collect(app, text, delay=0, kind="forensics")

        ammo = self._["PersonalAmmo"](
            ammo_type="personal",
            target_account=app,
            target_platform="通知来源",
            violation_time=now.isoformat(),
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
        self._ui_send({"type": "event", "time": ts_str, "source": app,
                       "keyword": self.kw.match(text) or "命中", "kind": "forensics"})
        self._ui_send({"type": "stats", "forensics": self._c_forensics, "evidence": self._c_evidence,
                       "anti": self._c_anti, "anti_tag": self._c_anti_tag})

        anti = self.cfg.anti_strike
        if anti.get("enabled") and self.kw.is_attack(text):
            evidence_files = list(attachments.get("screenshots", []))
            if attachments.get("replay"):
                evidence_files.append(attachments["replay"])

            cid = str(uuid.uuid4())
            ev = threading.Event()
            ev.data = None
            with _CONFIRM_RESP_LOCK:
                _CONFIRM_RESP[cid] = ev

            self._ui_send({
                "type": "confirm_req", "id": cid,
                "source": app, "text": text, "clause": self.cfg.default_clause,
                "timeout": anti.get("confirm_timeout", 30),
                "evidence_files": evidence_files,
                "target_account": "",
                "event_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            })

            ev.wait(timeout=anti.get("confirm_timeout", 30) + 5)
            approved = ev.data.get("approved", False) if ev.data else False
            clause = ev.data.get("clause", self.cfg.default_clause) if ev.data else self.cfg.default_clause

            if approved:
                ammo.clause = clause
                draft = ammo.to_draft_text()
                draft_path = os.path.join(self.cfg.save_path,
                                          f"report_draft_{now.strftime('%Y%m%d_%H%M%S')}.txt")
                with open(draft_path, "w", encoding="utf-8") as f:
                    f.write(draft)

                if self.cfg.channels.get("copy_ammo"):
                    try:
                        import pyperclip
                        pyperclip.copy(draft)
                    except Exception:
                        pass

                results = self.channels.dispatch_with_fallback(ammo, draft_path)
                for ch_name, ok, note in results:
                    self.db.log_counterstrike(event_id, ch_name, ok, note)

                self.bus.notify_counterstrike(ammo.to_dict())

                self._c_anti += 1
                self._ui_send({"type": "event", "time": ts_str, "source": app, "keyword": "反伤已发起", "kind": "anti"})
                self._ui_send({"type": "stats", "forensics": self._c_forensics, "evidence": self._c_evidence,
                               "anti": self._c_anti, "anti_tag": self._c_anti_tag})
                summary = "，".join(f"{n}{'✓' if ok else '✗'}" for n, ok, _ in results)
                self._log.info(f"反伤结果：{summary}")
                self._ui_send({"type": "notify", "title": "网安智盾 · 反伤", "message": f"已并发发起举报：{summary}"})
            else:
                self._log.info("用户放弃反伤")

        self._ui_send({"type": "notify", "title": "网安智盾", "message": f"已取证：{app}"})

    def _on_anti_tag_alert(self, alerts: list):
        for event_type, msg in alerts:
            self._c_anti_tag += 1
            self._ui_send({"type": "event", "time": datetime.now().strftime("%H:%M:%S"),
                           "source": "防点号", "keyword": msg, "kind": "anti_tag"})
            self.db.log_anti_tag(event_type, 0, 0, "alert")
        self._ui_send({"type": "stats", "forensics": self._c_forensics, "evidence": self._c_evidence,
                       "anti": self._c_anti, "anti_tag": self._c_anti_tag})

    def _freeze_entries(self):
        self._log.warning("触发入口自动冻结")
        self._ui_send({"type": "notify", "title": "网安智盾 · 防点号", "message": "检测到异常频率，已自动冻结入口"})

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
        self.kw.reload(config.keywords, attack_keywords=config.attack_keywords)
        self._ui_send({"type": "rec_state", "enabled": config.enable_recording})
        self._log.info("配置已热更新")

    def _toggle_monitor(self):
        self._paused = not self._paused
        if self.monitor:
            if self._paused:
                self.monitor.stop()
            else:
                self.monitor.start()
        running = not self._paused
        self._ui_send({"type": "running", "running": running})
        self._log.info("监听已" + ("恢复" if running else "暂停"))

    def _open_dir(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            self._log.warning(f"打开目录失败：{e}")

    def _show_about(self):
        import tkinter as tk
        from tkinter import messagebox
        try:
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
        from core.config import ConfigManager
        try:
            self.cfg = ConfigManager(self.cfg.path)
            self._apply_config(self.cfg)
            self._ui_send({"type": "notify", "title": "网安智盾", "message": "配置已重载"})
        except Exception as e:
            self._log.warning(f"重载配置失败：{e}")

    def _test_trigger(self):
        threading.Thread(target=lambda: self._on_trigger(
            "测试", "测试：模拟的恶意通知，用于验证取证链路。", time.time()), daemon=True).start()

    def _uptime_loop(self):
        while True:
            time.sleep(30)
            try:
                self._ui_send({"type": "uptime", "seconds": int(time.time() - self._start_ts)})
            except Exception:
                pass

    def start(self, start_minimized: bool = False):
        NotificationMonitor = self._["NotificationMonitor"]
        self.monitor = NotificationMonitor(self.kw, self._on_trigger)
        self.monitor.start()

        self._start_ui(start_minimized=start_minimized)
        self._ui_send({"type": "rec_state", "enabled": self.cfg.enable_recording})
        self._ui_send({"type": "obs_state", "enabled": self.cfg.obs.get("enabled", False)})
        self._ui_send({"type": "enc_state", "enabled": self.cfg.encrypt})
        self._ui_send({"type": "stats", "forensics": 0, "evidence": 0, "anti": 0, "anti_tag": 0})
        self._ui_send({"type": "uptime", "seconds": 0})

        self.cwas.register()
        self._log.info("CWAS 注册完成")

        threading.Thread(target=self._anti_tag_loop, daemon=True).start()
        threading.Thread(target=self._uptime_loop, daemon=True).start()
        self._log.info("网安智盾引擎已启动")

    def stop(self):
        if self.monitor:
            self.monitor.stop()
        self._ui_send({"type": "shutdown"})
        if self._ui_proc:
            try:
                self._ui_proc.wait(timeout=5)
            except Exception:
                try:
                    self._ui_proc.kill()
                except Exception:
                    pass
        self.db.close()
        self._log.info("网安智盾已退出")
        os._exit(0)


# ── 入口 ────────────────────────────────────────────────────

def _fatal_error(e: Exception):
    import traceback
    tb = traceback.format_exc()
    try:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        base = "."
    try:
        with open(os.path.join(base, "wangzhidun_crash.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] 致命错误:\n{tb}\n")
    except Exception:
        pass
    _early_msgbox("网安智盾 · 启动失败",
                  f"程序无法启动：{e}\n\n详情见 wangzhidun_crash.log")


def main():
    role = "--ui" if "--ui" in sys.argv else "engine"

    if role == "--ui":
        start_minimized = any(a in ("--minimized", "--startup", "-m") for a in sys.argv)
        _run_ui_process(sys.stdin, sys.stdout, start_minimized)
        return

    # ── 引擎模式 ──
    try:
        from core.config import ConfigManager
        from core.logger import log, setup_logger
        from core.crypto import EvidenceCrypto
        from core.coordination import CWASClient, CoordinationBus
        from db.database import Database

        from monitor.notify_listener import NotificationMonitor
        from monitor.keyword_match import KeywordEngine
        from monitor.freq_detect import AntiTag

        from forensics.archive import EvidenceManager

        from ammo.personal_ammo import PersonalAmmo

        from defense.harden_check import AntiReport

        from channel.manager import ChannelManager
    except ImportError as e:
        _early_msgbox("网安智盾 · 模块加载失败",
                      f"无法加载必要模块：{e}\n请重新下载或重新构建。")
        raise

    start_minimized = any(a in ("--minimized", "--startup", "-m") for a in sys.argv[1:])
    if "--debug" in sys.argv:
        import logging
        setup_logger(level=logging.DEBUG)

    app = WangAnZhiDun(
        ConfigManager=ConfigManager, KeywordEngine=KeywordEngine,
        EvidenceCrypto=EvidenceCrypto, NotificationMonitor=NotificationMonitor,
        EvidenceManager=EvidenceManager, ChannelManager=ChannelManager,
        AntiReport=AntiReport, AntiTag=AntiTag,
        CWASClient=CWASClient, CoordinationBus=CoordinationBus,
        log=log, Database=Database, PersonalAmmo=PersonalAmmo,
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
