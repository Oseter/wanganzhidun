"""配置窗口：tkinter 实现，普通用户零代码改配置。

可编辑项：监测关键词、证据路径、自带录屏、是否启用反伤、反伤超时。
保存即写回 config.ini。
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ConfigWindow:
    """配置 GUI。"""

    def __init__(self, config):
        self.config = config
        self.root = tk.Tk()
        self.root.title("网安智盾 · 设置")
        self.root.geometry("520x420")
        self._build()

    def _build(self):
        c = self.config
        f = ttk.Frame(self.root, padding=12)
        f.pack(fill="both", expand=True)

        # 关键词
        ttk.Label(f, text="监测关键词（逗号分隔）：").grid(row=0, column=0, sticky="w")
        self.kw_var = tk.StringVar(value=",".join(c.keywords))
        ttk.Entry(f, textvariable=self.kw_var, width=50).grid(row=1, column=0, columnspan=2, sticky="ew")

        # 证据路径
        ttk.Label(f, text="证据保存路径：").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.path_var = tk.StringVar(value=c.save_path)
        ttk.Entry(f, textvariable=self.path_var, width=40).grid(row=3, column=0, sticky="ew")
        ttk.Button(f, text="浏览", command=self._choose).grid(row=3, column=1, padx=4)

        # 自带录屏
        rec = c.recorder
        ttk.Label(f, text="自带录屏（无需OBS）：").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.rec_on = tk.BooleanVar(value=rec["enabled"])
        self.rec_fps = tk.StringVar(value=str(rec["fps"]))
        self.rec_buf = tk.StringVar(value=str(rec["buffer_seconds"]))
        self.rec_scale = tk.StringVar(value=str(rec["scale"]))
        ttk.Checkbutton(f, text="启用", variable=self.rec_on).grid(row=5, column=0, sticky="w")
        ttk.Label(f, text="帧率").grid(row=5, column=0, sticky="e")
        ttk.Entry(f, textvariable=self.rec_fps, width=6).grid(row=5, column=1, sticky="w", padx=4)
        ttk.Label(f, text="缓冲秒").grid(row=6, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.rec_buf, width=6).grid(row=6, column=0, sticky="e")
        ttk.Label(f, text="缩放").grid(row=6, column=1, sticky="w", padx=4)
        ttk.Entry(f, textvariable=self.rec_scale, width=6).grid(row=6, column=1, sticky="e")

        # 反伤
        anti = c.anti_strike
        ttk.Label(f, text="反伤：").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.anti_on = tk.BooleanVar(value=anti["enabled"])
        self.anti_to = tk.StringVar(value=str(anti["confirm_timeout"]))
        ttk.Checkbutton(f, text="启用反伤（需手动确认）", variable=self.anti_on).grid(row=7, column=0, sticky="w")
        ttk.Label(f, text="确认超时(秒)：").grid(row=7, column=1, sticky="w")
        ttk.Entry(f, textvariable=self.anti_to, width=6).grid(row=7, column=1, sticky="e")

        # 保存
        ttk.Button(f, text="保存", command=self._save).grid(row=8, column=0, pady=(16, 0))
        ttk.Button(f, text="关闭", command=self.root.destroy).grid(row=8, column=1, pady=(16, 0))

    def _choose(self):
        p = filedialog.askdirectory()
        if p:
            self.path_var.set(p)

    def _save(self):
        c = self.config
        c.set("monitor", "keywords", self.kw_var.get())
        c.set("evidence", "save_path", self.path_var.get())
        c.set("recorder", "enabled", str(self.rec_on.get()))
        c.set("recorder", "fps", self.rec_fps.get())
        c.set("recorder", "buffer_seconds", self.rec_buf.get())
        c.set("recorder", "scale", self.rec_scale.get())
        c.set("anti_strike", "enabled", str(self.anti_on.get()))
        c.set("anti_strike", "confirm_timeout", self.anti_to.get())
        messagebox.showinfo("网安智盾", "配置已保存，重启生效。")
        self.root.destroy()

    def run(self):
        self.root.mainloop()
