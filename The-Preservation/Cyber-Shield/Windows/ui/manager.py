"""统一 UI 管理器（UI 改进版）：网安智盾所有图形界面的唯一入口。

相对旧版改进：
    - add_event 增加 kind 参数（forensics / anti / test），支持事件列表按类型着色；
    - ask_confirm 增加可选 evidence_files / target_account / event_time，
      启用反伤弹窗的「标准弹药预览」与证据缩略图（向后兼容，缺省不影响旧调用）。

线程安全模型不变：所有 UI 操作经 self._queue 投递到 UI 线程泵执行。
"""
import queue
import threading
from typing import Callable, Dict, Optional

import tkinter as tk

class UIManager:
    """拥有唯一 Tk 根，管理主窗口 / 配置窗 / 确认弹窗。"""

    POLL_MS = 40  # UI 线程泵轮询间隔

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

    # ---------------- 生命周期 ----------------
    def start(self):
        self._ui_thread = threading.Thread(target=self._run, daemon=True)
        self._ui_thread.start()
        self._ready.wait(timeout=10)
        if getattr(self, "_startup_error", None):
            raise RuntimeError(f"UI 初始化失败：\n{self._startup_error}")

    def _run(self):
        # 延迟导入，避免打包时模块缺失导致整个 UI 线程崩溃
        try:
            from PIL import ImageTk  # noqa: F811
        except Exception:
            ImageTk = None
        from ui.main_window import MainWindow
        from ui.icons import window_logo

        try:
            self.root = tk.Tk()
            self.root.title("网安智盾 · WangAnZhiDun")
            self.root.withdraw()  # 先隐藏，构造完再显示，避免闪烁

            # Logo：ImageTk 不可用时降级跳过，不让整个窗口崩溃
            self.logo = None
            try:
                pil = window_logo(40)
                if ImageTk is not None:
                    self.logo = ImageTk.PhotoImage(pil)
            except Exception:
                pass

            self._main = MainWindow(self.root, {**self.cb, "logo": self.logo})
            self._ready.set()

            # 显示窗口：多重保证一定能弹出来
            if not self._start_minimized:
                try:
                    self.root.deiconify()
                except Exception:
                    pass
                try:
                    self.root.lift()
                except Exception:
                    pass
                try:
                    self.root.focus_force()
                except Exception:
                    pass
                try:
                    self.root.attributes("-topmost", True)
                    self.root.after(300, lambda: self.root.attributes("-topmost", False))
                except Exception:
                    pass
            # 即使最小化启动，也确保窗口已构造完毕（托盘可随时 show）

            self.root.after(self.POLL_MS, self._pump)
            self.root.mainloop()
        except Exception as e:  # noqa: BLE001
            import os
            import sys
            import traceback
            from datetime import datetime
            tb = traceback.format_exc()
            self._startup_error = tb
            try:
                from core.logger import log
                log.error(f"UI 线程启动失败：\n{tb}")
            except Exception:
                pass
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

    # ---------------- UI 线程泵 ----------------
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

    # ---------------- 线程安全调度 ----------------
    def _dispatch(self, fn: Callable[[], None]):
        self._queue.put(fn)

    def _safe(self, fn: Callable[[], None]):
        self._dispatch(fn)

    # ---------------- 主窗口显隐 ----------------
    def show(self):
        def _do_show():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.attributes("-topmost", True)
                self.root.after(300, lambda: self.root.attributes("-topmost", False))
            except Exception:
                pass
        self._dispatch(_do_show)
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

    # ---------------- 状态刷新 ----------------
    def set_running(self, running: bool):
        self._running = running
        self._dispatch(lambda: self._main.set_running(running))

    def set_rec_enabled(self, enabled: bool):
        self._dispatch(lambda: self._main.set_rec_enabled(enabled))

    def add_event(self, time_str: str, source: str, keyword: str,
                  kind: str = "forensics"):
        """新增事件到列表。kind 用于着色：forensics / anti / test / info。"""
        self._dispatch(lambda: self._main.add_event(time_str, source, keyword, kind))

    def set_stats(self, forensics: int, evidence: int, anti: int):
        self._dispatch(lambda: self._main.set_stats(forensics, evidence, anti))

    def set_uptime(self, seconds: int):
        self._dispatch(lambda: self._main.set_uptime(seconds))

    def copy_text(self, text: str):
        self._dispatch(lambda: (self.root.clipboard_clear(),
                                self.root.clipboard_append(text)))

    # ---------------- 配置窗 ----------------
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

    # ---------------- 确认弹窗（阻塞调用线程） ----------------
    def ask_confirm(self, source_app: str, text: str, clause: str,
                    timeout: int = 30, evidence_files=None,
                    target_account: str = "", event_time: str = "") -> bool:
        """阻塞当前线程直到用户确认 / 放弃 / 超时，返回 (是否确认, 条款)。

        新增可选参数（向后兼容）：
            evidence_files: 证据附件路径列表（启用弹窗缩略图与预览）；
            target_account: 目标账号（缺省由用户在举报通道填写）；
            event_time:     取证时间字符串。
        """
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
