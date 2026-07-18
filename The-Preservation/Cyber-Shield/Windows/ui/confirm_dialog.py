"""反伤确认弹窗：检测到攻击后弹出，用户手动确认才发起反伤举报。

红线：程序绝不自动举报，必须用户确认（对恶俗攻击目标的反制）。
弹窗展示攻击摘要与可编辑条款，带倒计时；超时未确认则自动放弃。

实现为 Toplevel，结果经由 on_result(bool) 回调返回（由 UIManager 阻塞等待）。
"""
import tkinter as tk
from tkinter import ttk


class ConfirmDialog:
    """反伤确认弹窗（非独立 Tk，挂在主根上）。"""

    def __init__(self, parent: tk.Tk, source_app: str, text: str,
                 clause: str, timeout: int = 30, on_result=None):
        self.on_result = on_result
        self._timeout = timeout
        self._remain = timeout
        self._after_id = None
        self._done = False

        self.top = tk.Toplevel(parent)
        self.top.title("网安智盾 · 反伤确认")
        self.top.geometry("460x320")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.attributes("-topmost", True)
        self.top.configure(bg="#eef2f7")
        self.top.protocol("WM_DELETE_WINDOW", lambda: self._finish(False))

        ttk.Label(self.top, text="检测到疑似攻击性通知",
                  font=("Microsoft YaHei", 13, "bold"),
                  foreground="#c0392b").pack(pady=(12, 2))
        ttk.Label(self.top, text=f"来源：{source_app}").pack(anchor="w", padx=18)

        txt = tk.Text(self.top, height=4, wrap="word",
                      font=("Microsoft YaHei", 9))
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(fill="x", padx=18, pady=6)

        ttk.Label(self.top, text="对应条款（可修改）：").pack(anchor="w", padx=18)
        self.clause_var = tk.StringVar(value=clause)
        ttk.Entry(self.top, textvariable=self.clause_var, width=54).pack(
            fill="x", padx=18)

        self._count_var = tk.StringVar(value=self._count_text())
        self._count = ttk.Label(self.top, textvariable=self._count_var,
                                foreground="#5b6b7b")
        self._count.pack(pady=(6, 0))

        bf = ttk.Frame(self.top)
        bf.pack(pady=10)
        ttk.Button(bf, text="确认反伤举报", style="Accent.TButton",
                   command=lambda: self._finish(True)).pack(side="left", padx=8)
        ttk.Button(bf, text="放弃", command=lambda: self._finish(False)).pack(
            side="left", padx=8)

    def _count_text(self):
        if self._timeout and self._timeout > 0:
            return f"{self._remain} 秒后自动放弃"
        return "不会自动关闭，请手动确认"

    def show(self):
        self.top.deiconify()
        self.top.lift()
        if self._timeout and self._timeout > 0:
            self._tick()

    def _tick(self):
        self._remain -= 1
        self._count_var.set(self._count_text())
        if self._remain <= 0:
            self._finish(False)
            return
        self._after_id = self.top.after(1000, self._tick)

    def _finish(self, value: bool):
        if self._done:
            return
        self._done = True
        if self._after_id:
            try:
                self.top.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self.top.destroy()
        except Exception:
            pass
        if callable(self.on_result):
            self.on_result(value, self.clause_var.get())
