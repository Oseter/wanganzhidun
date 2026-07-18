"""统一 UI 管理器：网安智盾所有图形界面的唯一入口。

设计要点（重要）：
    tkinter 不支持跨线程多 Tk() 实例，也**不支持跨线程调用任何 Tk 方法**
    （包括 root.after）。本工具既有系统托盘（pystray 线程），又有取证回调
    （monitor 线程）会弹确认窗，因此所有 tkinter 界面（主窗口 = 根 Tk，
    配置窗 / 确认弹窗 = 其上的 Toplevel）统一跑在**一个 UI 线程、一个 Tk 根** 上。

线程安全模型（关键）：
    UI 线程外**禁止直接触碰 Tk**。所有 UI 操作通过 self._queue（queue.Queue）
    投递，由 UI 线程内的 _pump 轮询循环取出并在 UI 线程上执行。_pump 自身用
    root.after(...) 重新调度，而 root.after 只会在 UI 线程内被调用，因此安全。
    这样即使主线程在 mainloop 启动前就调用 set_rec_enabled，也只会被安全入队，
    等 UI 线程就绪后由泵执行，不会出现 "main thread is not in main loop"。

UI 线程外调用（monitor / pystray / 主线程）：
    show / hide / toggle / set_running / add_event / set_stats / set_rec_enabled
    open_config / refresh  —— 非阻塞，仅投递刷新任务
    ask_confirm(...) —— 阻塞调用线程直到用户确认或超时（结果经回调返回）
"""
import queue
import threading
from typing import Callable, Dict, Optional

import tkinter as tk


class UIManager:
    """拥有唯一 Tk 根，管理主窗口 / 配置窗 / 确认弹窗。"""

    POLL_MS = 40  # UI 线程泵轮询间隔

    def __init__(self, callbacks: Dict):
        self.cb = callbacks
        self.root: Optional[tk.Tk] = None
        self._main = None
        self.logo = None
        self._ui_thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._config_dlg = None
        self._running = True
        # 跨线程安全投递队列：所有 UI 操作都进这里，由 UI 线程泵取出执行
        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()

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
        # 启动队列泵（root.after 仅在 UI 线程内调用，安全）
        self.root.after(self.POLL_MS, self._pump)
        self.root.mainloop()

    # ---------------- UI 线程泵（只在 UI 线程内运行） ----------------
    def _pump(self):
        try:
            while True:
                fn = self._queue.get_nowait()
                try:
                    fn()
                except Exception:
                    # 单个回调异常不应击垮泵
                    pass
                self._queue.task_done()
        except queue.Empty:
            pass

        # 继续轮询；仅在 UI 线程内调用 root.after，安全
        if self.root is not None:
            try:
                if self.root.winfo_exists():
                    self.root.after(self.POLL_MS, self._pump)
            except Exception:
                pass

    # ---------------- 线程安全调度（核心） ----------------
    def _dispatch(self, fn: Callable[[], None]):
        """把 UI 操作投递到队列。绝不在 UI 线程外直接调用 Tk 方法。"""
        self._queue.put(fn)

    # 历史别名，保持调用点兼容
    def _safe(self, fn: Callable[[], None]):
        self._dispatch(fn)

    # ---------------- 主窗口显隐 ----------------
    def show(self):
        self._dispatch(lambda: (self.root.deiconify(), self.root.lift()))
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
        # winfo_viewable 也是 Tk 调用，必须进队列在 UI 线程判断
        self._dispatch(self._toggle_now)

    def _toggle_now(self):
        if self.root is None:
            return
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.lift()

    # ---------------- 状态刷新（非阻塞） ----------------
    def set_running(self, running: bool):
        self._running = running
        self._dispatch(lambda: self._main.set_running(running))

    def set_rec_enabled(self, enabled: bool):
        self._dispatch(lambda: self._main.set_rec_enabled(enabled))

    def add_event(self, time_str: str, source: str, keyword: str):
        self._dispatch(lambda: self._main.add_event(time_str, source, keyword))

    def set_stats(self, forensics: int, evidence: int, anti: int):
        self._dispatch(lambda: self._main.set_stats(forensics, evidence, anti))

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

        self._dispatch(build)

    # ---------------- 确认弹窗（阻塞调用线程） ----------------
    def ask_confirm(self, source_app: str, text: str, clause: str,
                    timeout: int = 30) -> bool:
        """阻塞当前线程直到用户确认 / 放弃 / 超时，返回是否确认反伤。

        注意：必须从非 UI 线程调用（取证回调在 monitor 线程）。
        内部通过队列让 UI 线程构建弹窗，本线程仅等待 done 事件。
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
            # 不应在此路径调用；直接构建以防卡死（调用方需保证不在 UI 线程）
            build()
        else:
            self._dispatch(build)
        done.wait()
        return result["ok"]
