import queue
import threading
from typing import Callable, Dict, Optional

import tkinter as tk


class UIManager:
    POLL_MS = 40

    def __init__(self, callbacks: Dict, start_minimized: bool = False):
        self.cb = callbacks
        self.root: Optional[tk.Tk] = None
        self._main = None
        self.logo = None
        self._ui_thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._config_dlg = None
        self._running = True
        self._start_minimized = start_minimized
        self._startup_error = None
        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()

    def start(self):
        self._ui_thread = threading.Thread(target=self._run, daemon=True)
        self._ui_thread.start()
        self._ready.wait(timeout=10)
        if getattr(self, "_startup_error", None):
            raise RuntimeError(f"UI 初始化失败：\n{self._startup_error}")

    def _run(self):
        try:
            from PIL import ImageTk
        except Exception:
            ImageTk = None
        from ui.main_window import MainWindow
        from ui.icons import window_logo

        try:
            self.root = tk.Tk()
            self.root.title("网安智盾 · WangAnZhiDun")
            self.root.withdraw()

            self.logo = None
            try:
                pil = window_logo(40)
                if ImageTk is not None:
                    self.logo = ImageTk.PhotoImage(pil)
            except Exception:
                pass

            self._main = MainWindow(self.root, {**self.cb, "logo": self.logo})
            self._ready.set()

            if not self._start_minimized:
                try:
                    self.root.deiconify()
                    self.root.lift()
                    self.root.focus_force()
                    self.root.attributes("-topmost", True)
                    self.root.after(300, lambda: self.root.attributes("-topmost", False))
                except Exception:
                    pass

            self.root.after(self.POLL_MS, self._pump)
            self.root.mainloop()
        except Exception as e:
            import os
            import sys
            import traceback
            from datetime import datetime
            tb = traceback.format_exc()
            self._startup_error = tb
            try:
                base = os.path.dirname(os.path.abspath(sys.argv[0]))
            except Exception:
                base = "."
            try:
                with open(os.path.join(base, "wangzhidun_crash.log"),
                          "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now()}] UI 启动失败:\n{tb}\n")
            except Exception:
                pass
            self._ready.set()

    def _pump(self):
        try:
            while True:
                fn = self._queue.get_nowait()
                try:
                    fn()
                except Exception:
                    pass
                self._queue.task_done()
        except queue.Empty:
            pass
        if self.root is not None:
            try:
                if self.root.winfo_exists():
                    self.root.after(self.POLL_MS, self._pump)
            except Exception:
                pass

    def _dispatch(self, fn: Callable[[], None]):
        self._queue.put(fn)

    def show(self):
        def _do():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.attributes("-topmost", True)
                self.root.after(300, lambda: self.root.attributes("-topmost", False))
            except Exception:
                pass
        self._dispatch(_do)
        refresh = self.cb.get("on_refresh")
        if callable(refresh):
            try:
                res = refresh()
                if res:
                    events, stats = res
                    self._dispatch(lambda: self._main.refresh_events(events))
                    self._dispatch(lambda: self._main.set_stats(*stats))
            except Exception:
                pass

    def hide(self):
        self._dispatch(self.root.withdraw)

    def toggle(self):
        self._dispatch(self._toggle_now)

    def _toggle_now(self):
        if self.root is None:
            return
        try:
            if self.root.winfo_viewable():
                self.root.withdraw()
            else:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.attributes("-topmost", True)
                self.root.after(300, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def set_running(self, running: bool):
        self._running = running
        self._dispatch(lambda: self._main.set_running(running))

    def set_rec_enabled(self, enabled: bool):
        self._dispatch(lambda: self._main.set_rec_enabled(enabled))

    def set_obs_enabled(self, enabled: bool):
        self._dispatch(lambda: self._main.set_obs_enabled(enabled))

    def set_enc_enabled(self, enabled: bool):
        self._dispatch(lambda: self._main.set_enc_enabled(enabled))

    def add_event(self, time_str: str, source: str, keyword: str,
                  kind: str = "forensics"):
        self._dispatch(lambda: self._main.add_event(time_str, source, keyword, kind))

    def set_stats(self, forensics: int, evidence: int, anti: int, anti_tag: int = 0):
        self._dispatch(lambda: self._main.set_stats(forensics, evidence, anti, anti_tag))

    def set_uptime(self, seconds: int):
        self._dispatch(lambda: self._main.set_uptime(seconds))

    def copy_text(self, text: str):
        self._dispatch(lambda: (self.root.clipboard_clear(),
                                self.root.clipboard_append(text)))

    def open_config(self, config, on_applied: Callable = None):
        from ui.config_window import ConfigWindow
        def build():
            if self._config_dlg is not None:
                try:
                    if self._config_dlg.winfo_exists():
                        self._config_dlg.lift()
                        return
                except Exception:
                    pass
            self._config_dlg = ConfigWindow(self.root, config, on_applied)
            self._config_dlg.show()
        self._dispatch(build)

    def ask_confirm(self, source_app: str, text: str, clause: str,
                    timeout: int = 30, evidence_files=None,
                    target_account: str = "", event_time: str = "") -> tuple:
        from ui.confirm_dialog import ConfirmDialog
        result = {"ok": False, "clause": clause}
        done = threading.Event()

        def on_result(value: bool, clause_text: str = clause):
            result["ok"] = value
            result["clause"] = clause_text
            done.set()

        def build():
            dlg = ConfirmDialog(self.root, source_app, text, clause, timeout,
                                on_result, evidence_files=evidence_files,
                                target_account=target_account, event_time=event_time)
            dlg.show()

        if threading.current_thread() is self._ui_thread:
            build()
        else:
            self._dispatch(build)
        done.wait()
        return result["ok"], result["clause"]
