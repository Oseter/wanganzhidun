import os
import tkinter as tk
from tkinter import ttk

C_BG = "#eef2f7"
C_CARD = "#ffffff"
C_LINE = "#d7dee8"
C_TEXT = "#1b2733"
C_SUB = "#5b6b7b"
C_DANGER = "#c0392b"
C_OK = "#27ae60"
C_ACCENT = "#2178c8"


class ConfirmDialog:
    def __init__(self, parent: tk.Tk, source_app: str, text: str,
                 clause: str, timeout: int = 30, on_result=None,
                 evidence_files=None, target_account: str = "",
                 event_time: str = ""):
        self.on_result = on_result
        self._timeout = timeout
        self._remain = timeout
        self._after_id = None
        self._done = False
        self._thumbs = []

        self.top = tk.Toplevel(parent)
        self.top.title("网安智盾 · 反伤确认")
        self.top.geometry("520x500")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.attributes("-topmost", True)
        self.top.configure(bg=C_BG)
        self.top.protocol("WM_DELETE_WINDOW", lambda: self._finish(False))

        ttk.Label(self.top, text="检测到疑似攻击性通知",
                  font=("Microsoft YaHei", 13, "bold"),
                  foreground=C_DANGER).pack(pady=(12, 2))
        meta = f"来源：{source_app}" + (f"    时间：{event_time}" if event_time else "")
        ttk.Label(self.top, text=meta).pack(anchor="w", padx=18)

        ttk.Label(self.top, text="违规内容：", foreground=C_SUB).pack(
            anchor="w", padx=18, pady=(6, 0))
        txt = tk.Text(self.top, height=3, wrap="word", font=("Microsoft YaHei", 9))
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(fill="x", padx=18, pady=2)

        ammo = ttk.LabelFrame(self.top, text="标准弹药预览（将提交的内容）", foreground=C_TEXT)
        ammo.pack(fill="x", padx=14, pady=(6, 0))
        self._ammo_row(ammo, "目标账号", target_account or "（待在举报通道填写）")
        self._ammo_row(ammo, "取证时间", event_time or "—")
        self._ammo_row(ammo, "证据附件", self._fmt_files(evidence_files))

        if evidence_files:
            self._build_thumbs(ammo, evidence_files)

        ttk.Label(self.top, text="对应条款（可修改）：", foreground=C_SUB).pack(
            anchor="w", padx=18, pady=(6, 0))
        self.clause_var = tk.StringVar(value=clause)
        ttk.Entry(self.top, textvariable=self.clause_var, width=60).pack(fill="x", padx=18)

        self._count_var = tk.StringVar(value=self._count_text())
        pf = tk.Frame(self.top, bg=C_BG)
        pf.pack(fill="x", padx=18, pady=(8, 0))
        self._bar = ttk.Progressbar(pf, maximum=max(timeout, 1), value=timeout)
        self._bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._count = ttk.Label(pf, textvariable=self._count_var, foreground=C_SUB)
        self._count.pack(side="right")

        bf = ttk.Frame(self.top, bg=C_BG)
        bf.pack(pady=10)
        ttk.Button(bf, text="确认反伤举报", style="Accent.TButton",
                   command=lambda: self._finish(True)).pack(side="left", padx=8)
        ttk.Button(bf, text="放弃", style="Danger.TButton",
                   command=lambda: self._finish(False)).pack(side="left", padx=8)

        self.top.bind("<Return>", lambda e: self._finish(True))
        self.top.bind("<Escape>", lambda e: self._finish(False))

    def _ammo_row(self, parent, label: str, value: str):
        row = tk.Frame(parent, bg=C_BG)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=f"{label}：", bg=C_BG, fg=C_SUB, width=10,
                 anchor="w", font=("Microsoft YaHei", 9)).pack(side="left")
        tk.Label(row, text=value, bg=C_BG, fg=C_TEXT, anchor="w",
                 font=("Microsoft YaHei", 9), wraplength=380,
                 justify="left").pack(side="left", fill="x", expand=True)

    def _fmt_files(self, files):
        if not files:
            return "（无）"
        names = [os.path.basename(f) for f in files if isinstance(f, str)]
        return "；".join(names) if len(names) <= 4 else "；".join(names[:4]) + " …"

    def _build_thumbs(self, parent, files):
        import PIL.Image as PILImage
        import PIL.ImageTk as PILImageTk
        box = tk.Frame(parent, bg=C_BG)
        box.pack(fill="x", padx=8, pady=(2, 4))
        shown = 0
        for f in files:
            if shown >= 4:
                break
            if not (isinstance(f, str) and f.lower().endswith((".png", ".jpg", ".jpeg"))):
                continue
            try:
                im = PILImage.open(f)
                im.thumbnail((72, 72))
                ph = PILImageTk.PhotoImage(im)
                self._thumbs.append(ph)
                lbl = tk.Label(box, image=ph, bg=C_BG, relief="groove", bd=1)
                lbl.pack(side="left", padx=3)
                shown += 1
            except Exception:
                continue

    def _count_text(self):
        if self._timeout and self._timeout > 0:
            return f"{self._remain}s 后自动放弃"
        return "不会自动关闭，请手动确认"

    def show(self):
        self.top.deiconify()
        self.top.lift()
        if self._timeout and self._timeout > 0:
            self._tick()

    def _tick(self):
        self._remain -= 1
        self._count_var.set(self._count_text())
        try:
            self._bar.configure(value=max(self._remain, 0))
        except Exception:
            pass
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
