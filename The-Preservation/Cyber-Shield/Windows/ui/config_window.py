"""配置窗口：tkinter + ttk.Notebook 实现，普通用户零代码改配置。

六个页签覆盖 config.ini 全部字段：
    监测 / 证据 / 录屏 / 举报邮件 / 反伤 / 标准弹药

保存即写回 config.ini，并调用 on_applied(config) 让程序热更新
（重载关键词引擎、热更新录屏/截图/归档/举报配置），无需重启。
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ConfigWindow:
    """配置 GUI（作为主根的 Toplevel）。"""

    def __init__(self, parent: tk.Tk, config, on_applied=None):
        self.config = config
        self.on_applied = on_applied
        self.top = tk.Toplevel(parent)
        self.top.title("网安智盾 · 设置")
        self.top.geometry("560x460")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg="#eef2f7")

        self.note = ttk.Notebook(self.top)
        self.note.pack(fill="both", expand=True, padx=10, pady=10)

        self._vars = {}
        self._build_monitor()
        self._build_evidence()
        self._build_recorder()
        self._build_email()
        self._build_antistrike()
        self._build_ammo()

        # 底部按钮
        bf = tk.Frame(self.top, bg="#eef2f7")
        bf.pack(fill="x", pady=(0, 10))
        ttk.Button(bf, text="保存", command=self._save,
                   style="Accent.TButton").pack(side="right", padx=10)
        ttk.Button(bf, text="关闭", command=self.top.destroy).pack(side="right")

    def show(self):
        self.top.deiconify()
        self.top.lift()

    # ---------------- 小工具 ----------------
    def _v(self, key, default):
        if key not in self._vars:
            self._vars[key] = tk.StringVar(value=str(default))
        return self._vars[key]

    def _bool(self, key, default):
        if key not in self._vars:
            self._vars[key] = tk.BooleanVar(value=bool(default))
        return self._vars[key]

    def _tab(self, title):
        f = ttk.Frame(self.note)
        self.note.add(f, text=title)
        return f

    def _row(self, f, r, label, widget, hint=None):
        tk.Label(f, text=label, bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9)).grid(
            row=r, column=0, sticky="w", padx=10, pady=4)
        widget.grid(row=r, column=1, sticky="ew", padx=10, pady=4)
        if hint:
            tk.Label(f, text=hint, bg="#eef2f7", fg="#9aa5b1",
                     font=("Microsoft YaHei", 8)).grid(
                row=r, column=2, sticky="w", padx=4)
        return r + 1

    # ---------------- 监测 ----------------
    def _build_monitor(self):
        c = self.config
        f = self._tab("监测")
        f.columnconfigure(1, weight=1)

        tk.Label(f, text="监测关键词（每行一个，通知文本命中即取证）：",
                 bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        self._kw = tk.Text(f, height=4, width=50,
                           font=("Microsoft YaHei", 9))
        self._kw.insert("1.0", "\n".join(c.keywords))
        self._kw.grid(row=1, column=0, columnspan=3, sticky="ew",
                      padx=10, pady=4)

        r = 2
        r = self._row(f, r, "命中后自动截图",
                      ttk.Checkbutton(f, variable=self._bool("enable_screenshot",
                                                             c.enable_screenshot)))
        r = self._row(f, r, "命中后抓取循环缓冲录像",
                      ttk.Checkbutton(f, variable=self._bool("enable_recording",
                                                             c.enable_recording)))
        r = self._row(f, r, "取证静默延迟(秒)",
                      ttk.Entry(f, textvariable=self._v("capture_delay",
                                                        c.capture_delay), width=10),
                      "等恶意内容完整显示")
        r = self._row(f, r, "单次取证后冷却(秒)",
                      ttk.Entry(f, textvariable=self._v("cooldown",
                                                        c.cooldown), width=10),
                      "防同事件重复触发")

    # ---------------- 证据 ----------------
    def _build_evidence(self):
        c = self.config
        f = self._tab("证据")
        f.columnconfigure(1, weight=1)

        path_var = self._v("save_path", c.save_path)
        pe = ttk.Entry(f, textvariable=path_var, width=38)
        brow = ttk.Button(f, text="浏览", command=lambda: self._choose(path_var))
        r = 0
        r = self._row(f, r, "证据保存路径", pe)
        brow.grid(row=r - 1, column=2, padx=4, pady=4)

        r = self._row(f, r, "截图格式",
                      ttk.Combobox(f, textvariable=self._v("screenshot_format",
                                                           c.screenshot_format),
                                   values=["png", "jpg"], width=8,
                                   state="readonly"))
        r = self._row(f, r, "单事件最多截图(张)",
                      ttk.Entry(f, textvariable=self._v("max_screenshots",
                                                        c.max_screenshots), width=10))
        r = self._row(f, r, "证据本地 AES 加密",
                      ttk.Checkbutton(f, variable=self._bool("encrypt",
                                                             c.encrypt)))

    # ---------------- 录屏 ----------------
    def _build_recorder(self):
        rec = self.config.recorder
        f = self._tab("录屏")
        f.columnconfigure(1, weight=1)

        r = 0
        r = self._row(f, r, "启用自带循环缓冲录屏",
                      ttk.Checkbutton(f, variable=self._bool("rec_enabled",
                                                             rec["enabled"])),
                      "无需安装 OBS")
        r = self._row(f, r, "帧率(fps)",
                      ttk.Entry(f, textvariable=self._v("rec_fps",
                                                        rec["fps"]), width=10),
                      "建议 8~15")
        r = self._row(f, r, "缓冲时长(秒)",
                      ttk.Entry(f, textvariable=self._v("rec_buffer",
                                                        rec["buffer_seconds"]),
                                width=10), "可回溯窗口")
        r = self._row(f, r, "分辨率缩放",
                      ttk.Entry(f, textvariable=self._v("rec_scale",
                                                        rec["scale"]), width=10),
                      "0.5~1.0")
        r = self._row(f, r, "显示器编号",
                      ttk.Entry(f, textvariable=self._v("rec_monitor",
                                                        rec["monitor_index"]),
                                width=10), "1=主屏")

    # ---------------- 举报邮件 ----------------
    def _build_email(self):
        e = self.config.email
        f = self._tab("举报邮件")
        f.columnconfigure(1, weight=1)

        r = 0
        r = self._row(f, r, "SMTP 服务器",
                      ttk.Entry(f, textvariable=self._v("smtp_server",
                                                        e["smtp_server"]), width=30))
        r = self._row(f, r, "SMTP 端口",
                      ttk.Entry(f, textvariable=self._v("smtp_port",
                                                        e["smtp_port"]), width=10))
        r = self._row(f, r, "发件人邮箱",
                      ttk.Entry(f, textvariable=self._v("sender",
                                                        e["sender"]), width=30))
        r = self._row(f, r, "发件人授权码",
                      ttk.Entry(f, textvariable=self._v("sender_password",
                                                        e["sender_password"]),
                                width=30, show="*"))
        r = self._row(f, r, "接收邮箱(官方举报)",
                      ttk.Entry(f, textvariable=self._v("receiver",
                                                        e["receiver"]), width=30),
                      "如 jubao@12377.cn")
        tk.Label(f, text="留空则仅生成本地举报草稿，不发邮件。",
                 bg="#eef2f7", fg="#9aa5b1",
                 font=("Microsoft YaHei", 8)).grid(
            row=r, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 0))

    # ---------------- 反伤 ----------------
    def _build_antistrike(self):
        a = self.config.anti_strike
        f = self._tab("反伤")
        f.columnconfigure(1, weight=1)

        r = 0
        r = self._row(f, r, "启用反伤（需手动确认）",
                      ttk.Checkbutton(f, variable=self._bool("anti_enabled",
                                                             a["enabled"])),
                      "程序绝不自动举报")
        r = self._row(f, r, "确认弹窗超时(秒)",
                      ttk.Entry(f, textvariable=self._v("anti_timeout",
                                                        a["confirm_timeout"]),
                                width=10), "0=不自动关闭")
        r = self._row(f, r, "反伤目标须含攻击性关键词",
                      ttk.Checkbutton(f,
                                      variable=self._bool("anti_req_kw",
                                                          a["require_attack_keyword"])))

    # ---------------- 标准弹药 ----------------
    def _build_ammo(self):
        f = self._tab("标准弹药")
        f.columnconfigure(1, weight=1)
        tk.Label(f, text="默认对应条款（确认弹窗中可改）：",
                 bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        self._clause = tk.Text(f, height=3, width=50,
                               font=("Microsoft YaHei", 9))
        self._clause.insert("1.0", self.config.default_clause)
        self._clause.grid(row=1, column=0, columnspan=3, sticky="ew",
                          padx=10, pady=4)
        tk.Label(f, text="标准弹药格式：目标账号 | 时间 | 违规内容 | 对应条款 | 证据附件",
                 bg="#eef2f7", fg="#9aa5b1",
                 font=("Microsoft YaHei", 8)).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=10, pady=4)

    # ---------------- 辅助 ----------------
    def _choose(self, var):
        p = filedialog.askdirectory()
        if p:
            var.set(p)

    # ---------------- 保存 ----------------
    def _save(self):
        c = self.config
        # 关键词：文本逐行 -> 逗号分隔
        kws = [k.strip() for k in self._kw.get("1.0", "end").splitlines()
               if k.strip()]
        try:
            cap_d = int(self._vars["capture_delay"].get())
            cool = int(self._vars["cooldown"].get())
            max_s = int(self._vars["max_screenshots"].get())
            fps = int(self._vars["rec_fps"].get())
            buf = int(self._vars["rec_buffer"].get())
            mon = int(self._vars["rec_monitor"].get())
            port = int(self._vars["smtp_port"].get())
            scale = float(self._vars["rec_scale"].get())
            timeout = int(self._vars["anti_timeout"].get())
            if not (1 <= fps <= 60):
                raise ValueError("帧率需在 1~60")
            if not (1 <= buf <= 600):
                raise ValueError("缓冲时长需在 1~600 秒")
            if not (0.5 <= scale <= 1.0):
                raise ValueError("缩放需在 0.5~1.0")
        except ValueError as e:
            messagebox.showerror("网安智盾", f"数值格式有误：{e}")
            return

        # 监测
        c.set("monitor", "keywords", ",".join(kws))
        c.set("monitor", "enable_screenshot", str(self._vars["enable_screenshot"].get()))
        c.set("monitor", "enable_recording", str(self._vars["enable_recording"].get()))
        c.set("monitor", "capture_delay", str(cap_d))
        c.set("monitor", "cooldown", str(cool))
        # 证据
        c.set("evidence", "save_path", self._vars["save_path"].get())
        c.set("evidence", "screenshot_format", self._vars["screenshot_format"].get())
        c.set("evidence", "max_screenshots", str(max_s))
        c.set("evidence", "encrypt", str(self._vars["encrypt"].get()))
        # 录屏
        c.set("recorder", "enabled", str(self._vars["rec_enabled"].get()))
        c.set("recorder", "fps", str(fps))
        c.set("recorder", "buffer_seconds", str(buf))
        c.set("recorder", "scale", str(scale))
        c.set("recorder", "monitor_index", str(mon))
        # 邮件
        c.set("email", "smtp_server", self._vars["smtp_server"].get())
        c.set("email", "smtp_port", str(port))
        c.set("email", "sender", self._vars["sender"].get())
        c.set("email", "sender_password", self._vars["sender_password"].get())
        c.set("email", "receiver", self._vars["receiver"].get())
        # 反伤
        c.set("anti_strike", "enabled", str(self._vars["anti_enabled"].get()))
        c.set("anti_strike", "confirm_timeout", str(timeout))
        c.set("anti_strike", "require_attack_keyword",
              str(self._vars["anti_req_kw"].get()))
        # 标准弹药
        c.set("standard_ammo", "default_clause",
              self._clause.get("1.0", "end").strip())

        if callable(self.on_applied):
            try:
                self.on_applied(c)
            except Exception as e:
                messagebox.showwarning("网安智盾", f"配置已保存，但热更新失败：{e}")
        messagebox.showinfo("网安智盾", "配置已保存并即时生效。")
        self.top.destroy()
