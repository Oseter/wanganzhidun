"""反伤确认弹窗：检测到攻击后弹出，用户手动确认才发起反伤举报。

红线：程序绝不自动举报，必须用户确认（对恶俗攻击目标的反制）。
弹窗展示攻击摘要，超时未确认则自动放弃。
"""
import tkinter as tk
from tkinter import ttk


class ConfirmDialog:
    """反伤确认弹窗（阻塞式，返回 True/False）。"""

    @staticmethod
    def ask(source_app: str, text: str, clause: str,
            timeout: int = 30) -> bool:
        result = {"ok": False}

        root = tk.Tk()
        root.title("网安智盾 · 反伤确认")
        root.geometry("420x260")
        root.attributes("-topmost", True)

        ttk.Label(root, text="检测到疑似攻击性通知", font=(None, 12, "bold")).pack(pady=(12, 4))
        ttk.Label(root, text=f"来源：{source_app}").pack(anchor="w", padx=16)
        txt = tk.Text(root, height=4, wrap="word")
        txt.insert("1.0", text)
        txt.config(state="disabled")
        txt.pack(fill="x", padx=16, pady=6)

        clause_var = tk.StringVar(value=clause)
        ttk.Label(root, text="对应条款：").pack(anchor="w", padx=16)
        ttk.Entry(root, textvariable=clause_var, width=50).pack(fill="x", padx=16)

        def do_confirm():
            result["ok"] = True
            root.destroy()

        def do_cancel():
            result["ok"] = False
            root.destroy()

        btn_f = ttk.Frame(root)
        btn_f.pack(pady=10)
        ttk.Button(btn_f, text="确认反伤举报", command=do_confirm).pack(side="left", padx=8)
        ttk.Button(btn_f, text="放弃", command=do_cancel).pack(side="left", padx=8)

        # 超时自动放弃
        if timeout and timeout > 0:
            root.after(timeout * 1000, do_cancel)

        root.mainloop()
        return result["ok"]
