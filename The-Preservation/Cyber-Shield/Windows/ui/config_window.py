import tkinter as tk
from tkinter import ttk, filedialog, messagebox

RECO_KEYWORDS = [
    "傻逼", "废物", "去死", "人肉", "挂人", "开盒", "约架",
    "引战", "威胁", "上门", "弄死你", "曝光你", "全家", "祖安",
]


class ConfigWindow:
    def __init__(self, parent: tk.Tk, config, on_applied=None):
        self.config = config
        self.on_applied = on_applied
        self.top = tk.Toplevel(parent)
        self.top.title("网安智盾 · 设置")
        self.top.geometry("600x560")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg="#eef2f7")

        self.note = ttk.Notebook(self.top)
        self.note.pack(fill="both", expand=True, padx=10, pady=10)

        self._vars = {}
        self._build_monitor()
        self._build_evidence()
        self._build_recorder()
        self._build_channels()
        self._build_email()
        self._build_antistrike()
        self._build_ammo()

        bf = tk.Frame(self.top, bg="#eef2f7")
        bf.pack(fill="x", pady=(0, 10))
        ttk.Button(bf, text="保存", command=self._save,
                   style="Accent.TButton").pack(side="right", padx=10)
        ttk.Button(bf, text="关闭", command=self.top.destroy).pack(side="right")

    def show(self):
        self.top.deiconify()
        self.top.lift()

    def _v(self, key, default):
        if key not in self._vars:
            self._vars[key] = tk.StringVar(value=str(default))
        return self._vars[key]

    def _bool(self, key, default):
        if key not in self._vars:
            self._vars[key] = tk.BooleanVar(value=bool(default))
        return self._vars[key]

    def _tab(self, title, banner=""):
        f = ttk.Frame(self.note)
        self.note.add(f, text=title)
        if banner:
            tk.Label(f, text=banner, bg="#eaf1f8", fg="#185a96",
                     font=("Microsoft YaHei", 9), anchor="w",
                     padx=10, pady=6, relief="flat").pack(fill="x", padx=8, pady=6)
        return f

    def _group(self, parent, title):
        g = tk.LabelFrame(parent, text=title, bg="#eef2f7", fg="#1b2733",
                          font=("Microsoft YaHei", 9, "bold"))
        g.pack(fill="x", padx=10, pady=(2, 8))
        g.columnconfigure(1, weight=1)
        return g

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

    def _build_monitor(self):
        c = self.config
        f = self._tab("监测", "命中以下关键词即自动取证（截图 / 录屏 / 归档）。")
        g = self._group(f, "关键词")
        tk.Label(g, text="监测关键词（每行一个）：",
                 bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        self._kw = tk.Text(g, height=4, width=50, font=("Microsoft YaHei", 9))
        self._kw.insert("1.0", "\n".join(c.keywords))
        self._kw.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
        ttk.Button(g, text="载入推荐关键词", command=self._add_reco).grid(
            row=2, column=0, sticky="w", padx=10, pady=2)

        g2 = self._group(f, "取证行为")
        r = 0
        r = self._row(g2, r, "自动截图",
                       ttk.Checkbutton(g2, variable=self._bool("enable_screenshot", c.enable_screenshot)))
        r = self._row(g2, r, "自动录屏",
                       ttk.Checkbutton(g2, variable=self._bool("enable_recording", c.enable_recording)))
        r = self._row(g2, r, "静默延迟(秒)",
                       ttk.Entry(g2, textvariable=self._v("capture_delay", c.capture_delay), width=10))
        r = self._row(g2, r, "冷却(秒)",
                       ttk.Entry(g2, textvariable=self._v("cooldown", c.cooldown), width=10))

    def _add_reco(self):
        existing = {k.strip() for k in self._kw.get("1.0", "end").splitlines() if k.strip()}
        add = [w for w in RECO_KEYWORDS if w not in existing]
        if add:
            cur = self._kw.get("1.0", "end")
            if cur.strip():
                self._kw.insert("end", "\n")
            self._kw.insert("end", "\n".join(add))
            messagebox.showinfo("网安智盾", f"已追加 {len(add)} 个推荐关键词")
        else:
            messagebox.showinfo("网安智盾", "推荐关键词已全部存在")

    def _build_evidence(self):
        c = self.config
        f = self._tab("证据", "取证文件保存与加密。")
        g = self._group(f, "存储")
        path_var = self._v("save_path", c.save_path)
        pe = ttk.Entry(g, textvariable=path_var, width=38)
        r = 0
        r = self._row(g, r, "证据路径", pe)
        ttk.Button(g, text="浏览", command=lambda: self._choose(path_var)).grid(
            row=r - 1, column=2, padx=4, pady=4)
        r = self._row(g, r, "截图格式",
                       ttk.Combobox(g, textvariable=self._v("screenshot_format", c.screenshot_format),
                                    values=["png", "jpg"], width=8, state="readonly"))
        r = self._row(g, r, "最多截图",
                       ttk.Entry(g, textvariable=self._v("max_screenshots", c.max_screenshots), width=10))
        r = self._row(g, r, "AES 加密",
                       ttk.Checkbutton(g, variable=self._bool("encrypt", c.encrypt)))

    def _build_recorder(self):
        f = self._tab("录屏", "OBS Studio 对接（需安装 OBS + obs-websocket 插件）。")
        obs = self.config.obs
        g = self._group(f, "OBS WebSocket")
        r = 0
        r = self._row(g, r, "启用 OBS",
                       ttk.Checkbutton(g, variable=self._bool("obs_enabled", obs.get("enabled", False))))
        r = self._row(g, r, "主机",
                       ttk.Entry(g, textvariable=self._v("obs_host", obs.get("host", "127.0.0.1")), width=20))
        r = self._row(g, r, "端口",
                       ttk.Entry(g, textvariable=self._v("obs_port", obs.get("port", 4455)), width=10))
        r = self._row(g, r, "密码",
                       ttk.Entry(g, textvariable=self._v("obs_password", obs.get("password", "")), width=20, show="*"))
        r = self._row(g, r, "缓冲时长(秒)",
                       ttk.Entry(g, textvariable=self._v("obs_buffer", obs.get("replay_buffer_seconds", 60)), width=10))

    def _build_channels(self):
        f = self._tab("通道", "反伤发射通道，主通道失败时自动降级到备用。")
        ch = self.config.channels
        g = self._group(f, "通道开关")
        r = 0
        r = self._row(g, r, "12377 官网",
                       ttk.Checkbutton(g, variable=self._bool("ch_web12377", ch.get("web_12377", True))))
        r = self._row(g, r, "举报邮箱",
                       ttk.Checkbutton(g, variable=self._bool("ch_email12377", ch.get("email_12377", True))))
        r = self._row(g, r, "腾讯卫士",
                       ttk.Checkbutton(g, variable=self._bool("ch_guard", ch.get("guard", True))))
        r = self._row(g, r, "省网信办备用",
                       ttk.Checkbutton(g, variable=self._bool("ch_provincial", ch.get("provincial", False))))
        r = self._row(g, r, "工信部备用",
                       ttk.Checkbutton(g, variable=self._bool("ch_miit", ch.get("miit", False))))
        r = self._row(g, r, "举报邮箱地址",
                       ttk.Entry(g, textvariable=self._v("ch_email_receiver", ch.get("email_receiver", "jubao@12377.cn")), width=30))
        r = self._row(g, r, "复制草稿到剪贴板",
                       ttk.Checkbutton(g, variable=self._bool("ch_copy_ammo", ch.get("copy_ammo", True))))

    def _build_email(self):
        e = self.config.email
        f = self._tab("邮件", "SMTP 配置，用于发送举报邮件。")
        g = self._group(f, "SMTP")
        r = 0
        r = self._row(g, r, "SMTP 服务器",
                       ttk.Entry(g, textvariable=self._v("smtp_server", e.get("smtp_server", "")), width=30))
        r = self._row(g, r, "端口",
                       ttk.Entry(g, textvariable=self._v("smtp_port", e.get("smtp_port", 587)), width=10))
        r = self._row(g, r, "发件人",
                       ttk.Entry(g, textvariable=self._v("sender", e.get("sender", "")), width=30))
        r = self._row(g, r, "授权码",
                       ttk.Entry(g, textvariable=self._v("sender_password", e.get("sender_password", "")), width=30, show="*"))

    def _build_antistrike(self):
        a = self.config.anti_strike
        f = self._tab("反伤", "检测到攻击后弹出确认框，你确认才发起。")
        g = self._group(f, "反伤设置")
        r = 0
        r = self._row(g, r, "启用反伤",
                       ttk.Checkbutton(g, variable=self._bool("anti_enabled", a.get("enabled", False))))
        r = self._row(g, r, "确认超时(秒)",
                       ttk.Entry(g, textvariable=self._v("anti_timeout", a.get("confirm_timeout", 30)), width=10))
        r = self._row(g, r, "需含攻击关键词",
                       ttk.Checkbutton(g, variable=self._bool("anti_req_kw", a.get("require_attack_keyword", True))))

    def _build_ammo(self):
        f = self._tab("弹药", "默认对应条款。")
        g = self._group(f, "默认条款")
        tk.Label(g, text="默认对应条款（确认弹窗中可改）：",
                 bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        self._clause = tk.Text(g, height=3, width=50, font=("Microsoft YaHei", 9))
        self._clause.insert("1.0", self.config.default_clause)
        self._clause.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=4)

    def _choose(self, var):
        p = filedialog.askdirectory()
        if p:
            var.set(p)

    def _save(self):
        c = self.config
        kws = [k.strip() for k in self._kw.get("1.0", "end").splitlines() if k.strip()]
        try:
            cap_d = int(self._vars["capture_delay"].get())
            cool = int(self._vars["cooldown"].get())
            max_s = int(self._vars["max_screenshots"].get())
        except ValueError as e:
            messagebox.showerror("网安智盾", f"数值格式有误：{e}")
            return

        c.set("monitor", "keywords", ",".join(kws))
        c.set("monitor", "enable_screenshot", str(self._vars["enable_screenshot"].get()))
        c.set("monitor", "enable_recording", str(self._vars["enable_recording"].get()))
        c.set("monitor", "capture_delay", str(cap_d))
        c.set("monitor", "cooldown", str(cool))
        c.set("evidence", "save_path", self._vars["save_path"].get())
        c.set("evidence", "screenshot_format", self._vars["screenshot_format"].get())
        c.set("evidence", "max_screenshots", str(max_s))
        c.set("evidence", "encrypt", str(self._vars["encrypt"].get()))
        c.set("obs", "enabled", str(self._vars["obs_enabled"].get()))
        c.set("obs", "host", self._vars["obs_host"].get())
        c.set("obs", "port", self._vars["obs_port"].get())
        c.set("obs", "password", self._vars["obs_password"].get())
        c.set("obs", "replay_buffer_seconds", self._vars["obs_buffer"].get())
        c.set("channels", "web_12377", str(self._vars["ch_web12377"].get()))
        c.set("channels", "email_12377", str(self._vars["ch_email12377"].get()))
        c.set("channels", "guard", str(self._vars["ch_guard"].get()))
        c.set("channels", "provincial", str(self._vars["ch_provincial"].get()))
        c.set("channels", "miit", str(self._vars["ch_miit"].get()))
        c.set("channels", "email_receiver", self._vars["ch_email_receiver"].get())
        c.set("channels", "copy_ammo", str(self._vars["ch_copy_ammo"].get()))
        c.set("email", "smtp_server", self._vars["smtp_server"].get())
        c.set("email", "smtp_port", self._vars["smtp_port"].get())
        c.set("email", "sender", self._vars["sender"].get())
        c.set("email", "sender_password", self._vars["sender_password"].get())
        c.set("anti_strike", "enabled", str(self._vars["anti_enabled"].get()))
        c.set("anti_strike", "confirm_timeout", self._vars["anti_timeout"].get())
        c.set("anti_strike", "require_attack_keyword", str(self._vars["anti_req_kw"].get()))
        c.set("standard_ammo", "default_clause", self._clause.get("1.0", "end").strip())

        if callable(self.on_applied):
            try:
                self.on_applied(c)
            except Exception as e:
                messagebox.showwarning("网安智盾", f"配置已保存，但热更新失败：{e}")
        messagebox.showinfo("网安智盾", "配置已保存。")
        self.top.destroy()
