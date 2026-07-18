"""统一 UI 管理器：网安智盾所有图形界面的唯一入口。

设计要点（重要）：
    tkinter 不支持跨线程多 Tk() 实例。本工具既有系统托盘（pystray 线程），
    又有取证回调（monitor 线程）会弹出确认窗，因此所有 tkinter 界面
    （主窗口 = 根 Tk，配置窗 / 确认弹窗 = 其上的 Toplevel）统一跑在
    **一个 UI 线程、一个 Tk 根** 上。对外暴露的方法都通过 root.after(0, ...)
    线程安全地调度到 UI 线程执行。

UI 线程外调用（monitor / pystray 线程）：
    show / hide / set_running / add_event / set_stats / refresh
        —— 非阻塞，仅投递刷新任务
    ask_confirm(...) —— 阻塞调用线程直到用户确认或超时（结果经回调返回）
"""
import threading
from typing import Callable, Dict, Optional, Tuple

import tkinter as tk


class UIManager:
    """拥有唯一 Tk 根，管理主窗口 / 配置窗 / 确认弹窗。"""

    def __init__(self, callbacks: Dict):
        self.cb = callbacks
        self.root: Optional[tk.Tk] = None
        self._main = None
        self.logo = None
        self._ui_thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._config_dlg = None
        self._running = True

    # ---------------- 生命周期 ----------------
    def start(self):
        self._ui_thread = threading.Thread(target=self._run, daemon=True)
        self._ui_thread.start()
        # 等根窗口就绪，保证后续调用 root 非 None
        self._ready.wait(timeout=10)

    def _run(self):
        from PIL import ImageTk
        from ui.main_window import MainWindow
        from ui.icons import window_logo

        self.root = tk.Tk()
        pil = window_logo(40)
        try:
            self.logo = ImageTk.PhotoImage(pil)
        except Exception:
            self.logo = None

        self._main = MainWindow(self.root, {**self.cb, "logo": self.logo})
        self._ready.set()
        self.root.mainloop()

    # ---------------- 线程安全调度 ----------------
    def _safe(self, fn: Callable):
        if self.root is None:
            return
        if threading.current_thread() is self._ui_thread:
            fn()
        else:
            self.root.after(0, fn)

    # ---------------- 主窗口显隐 ----------------
    def show(self):
        self._safe(lambda: (self.root.deiconify(), self.root.lift()))
        refresh = self.cb.get("on_refresh")
        if callable(refresh):
            try:
                res = refresh()
                if res:
                    events, stats = res
                    self._safe(lambda: self._main.refresh_events(events))
                    self._safe(lambda: self._main.set_stats(*stats))
            except Exception:
                pass

    def hide(self):
        self._safe(self.root.withdraw)

    def toggle(self):
        if self.root and self.root.winfo_viewable():
            self.hide()
        else:
            self.show()

    # ---------------- 状态刷新（非阻塞） ----------------
    def set_running(self, running: bool):
        self._running = running
        self._safe(lambda: self._main.set_running(running))

    def set_rec_enabled(self, enabled: bool):
        self._safe(lambda: self._main.set_rec_enabled(enabled))

    def add_event(self, time_str: str, source: str, keyword: str):
        self._safe(lambda: self._main.add_event(time_str, source, keyword))

    def set_stats(self, forensics: int, evidence: int, anti: int):
        self._safe(lambda: self._main.set_stats(forensics, evidence, anti))

    # ---------------- 配置窗（非阻塞） ----------------
    def open_config(self, config, on_applied: Callable = None):
        from ui.config_window import ConfigWindow

        def build():
            # 已有则置顶，避免叠加
            if self._config_dlg is not None:
                try:
                    if self._config_dlg.winfo_exists():
                        self._config_dlg.lift()
                        return
                except Exception:
                    pass
            self._config_dlg = ConfigWindow(self.root, config, on_applied)
            self._config_dlg.show()

        self._safe(build)

    # ---------------- 确认弹窗（阻塞调用线程） ----------------
    def ask_confirm(self, source_app: str, text: str, clause: str,
                    timeout: int = 30) -> bool:
        """阻塞当前线程直到用户确认 / 放弃 / 超时，返回是否确认反伤。

        注意：必须从非 UI 线程调用（取证回调在 monitor 线程）。
        """
        from ui.confirm_dialog import ConfirmDialog

        result = {"ok": False}
        done = threading.Event()

        def on_result(value: bool):
            result["ok"] = value
            done.set()

        def build():
            dlg = ConfirmDialog(self.root, source_app, text, clause, timeout,
                                on_result)
            dlg.show()

        if threading.current_thread() is self._ui_thread:
            # 不应在此路径调用；直接构建以防卡死
            build()
        else:
            self.root.after(0, build)
        done.wait()
        return result["ok"]
