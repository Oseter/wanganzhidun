"""配置窗口（UI 改进版）：tkinter + ttk.Notebook，普通用户零代码改配置。

相对旧版改进：
    - 每个页签增加「说明横幅」，解释该页作用；
    - 字段用 LabelFrame 分组，结构更清晰；
    - 监测页增加「载入推荐关键词」按钮（从本地合规词库追加，不覆盖现有）；
    - 底部增加「恢复默认」仅作用于可安全重置的参数（录屏推荐值）；
    - 保存逻辑与配置字段完全保持兼容（c.set / c.xxx 不变），热更新照旧。

六个页签：监测 / 证据 / 录屏 / 举报邮件 / 反伤 / 标准弹药。
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 本地合规推荐词库（用于监测针对本人的攻击性通知；防御用途，非攻击词）
RECO_KEYWORDS = [
    "傻逼", "废物", "去死", "人肉", "挂人", "开盒", "约架",
    "引战", "威胁", "上门", "弄死你", "曝光你", "全家", "祖安",
]


class ConfigWindow:
    """配置 GUI（作为主根的 Toplevel）。"""

    def __init__(self, parent: tk.Tk, config, on_applied=None):
        self.config = config
        self.on_applied = on_applied
        self.top = tk.Toplevel(parent)
        self.top.title("网安智盾 · 设置")
        self.top.geometry("580x500")
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

        bf = tk.Frame(self.top, bg="#eef2f7")
        bf.pack(fill="x", pady=(0, 10))
        ttk.Button(bf, text="保存", command=self._save,
                   style="Accent.TButton").pack(side="right", padx=10)
        ttk.Button(bf, text="恢复默认(录屏)", command=self._reset_rec).pack(
            side="right", padx=4)
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

    # ---------------- 监测 ----------------
    def _build_monitor(self):
        c = self.config
        f = self._tab("监测", "命中以下关键词即自动取证（截图 / 录屏 / 归档）。")
        g = self._group(f, "关键词")
        tk.Label(g, text="监测关键词（每行一个，通知文本命中即取证）：",
                 bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        self._kw = tk.Text(g, height=4, width=50,
                           font=("Microsoft YaHei", 9))
        self._kw.insert("1.0", "\n".join(c.keywords))
        self._kw.grid(row=1, column=0, columnspan=3, sticky="ew",
                      padx=10, pady=4)
        ttk.Button(g, text="载入推荐关键词", command=self._add_reco).grid(
            row=2, column=0, sticky="w", padx=10, pady=2)

        g2 = self._group(f, "取证行为")
        r = 0
        r = self._row(g2, r, "命中后自动截图",
                      ttk.Checkbutton(g2, variable=self._bool("enable_screenshot",
                                                              c.enable_screenshot)))
        r = self._row(g2, r, "命中后抓取循环缓冲录像",
                      ttk.Checkbutton(g2, variable=self._bool("enable_recording",
                                                              c.enable_recording)))
        r = self._row(g2, r, "取证静默延迟(秒)",
                      ttk.Entry(g2, textvariable=self._v("capture_delay",
                                                         c.capture_delay), width=10),
                      "等恶意内容完整显示")
        r = self._row(g2, r, "单次取证后冷却(秒)",
                      ttk.Entry(g2, textvariable=self._v("cooldown",
                                                         c.cooldown), width=10),
                      "防同事件重复触发")

    def _add_reco(self):
        existing = {k.strip() for k in self._kw.get("1.0", "end").splitlines() if k.strip()}
        add = [w for w in RECO_KEYWORDS if w not in existing]
        if add:
            cur = self._kw.get("1.0", "end")
            if cur.strip():
                self._kw.insert("end", "\n")
            self._kw.insert("end", "\n".join(add))
            messagebox.showinfo("网安智盾", f"已追加 {len(add)} 个推荐关键词（不覆盖现有）。")
        else:
            messagebox.showinfo("网安智盾", "推荐关键词已全部存在。")

    # ---------------- 证据 ----------------
    def _build_evidence(self):
        c = self.config
        f = self._tab("证据", "取证文件保存位置与加密方式。")
        g = self._group(f, "存储")
        path_var = self._v("save_path", c.save_path)
        pe = ttk.Entry(g, textvariable=path_var, width=38)
        r = 0
        r = self._row(g, r, "证据保存路径", pe)
        ttk.Button(g, text="浏览", command=lambda: self._choose(path_var)).grid(
            row=r - 1, column=2, padx=4, pady=4)

        r = self._row(g, r, "截图格式",
                      ttk.Combobox(g, textvariable=self._v("screenshot_format",
                                                           c.screenshot_format),
                                   values=["png", "jpg"], width=8,
                                   state="readonly"))
        r = self._row(g, r, "单事件最多截图(张)",
                      ttk.Entry(g, textvariable=self._v("max_screenshots",
                                                        c.max_screenshots), width=10))
        r = self._row(g, r, "证据本地 AES 加密",
                      ttk.Checkbutton(g, variable=self._bool("encrypt",
                                                             c.encrypt)))

    # ---------------- 录屏 ----------------
    def _build_recorder(self):
        rec = self.config.recorder
        f = self._tab("录屏", "自带循环缓冲录屏，无需安装 OBS，纯 CPU 软编码。")
        g = self._group(f, "循环缓冲录屏")
        r = 0
        r = self._row(g, r, "启用自带循环缓冲录屏",
                      ttk.Checkbutton(g, variable=self._bool("rec_enabled",
                                                             rec["enabled"])),
                      "无需安装 OBS")
        r = self._row(g, r, "帧率(fps)",
                      ttk.Entry(g, textvariable=self._v("rec_fps",
                                                        rec["fps"]), width=10),
                      "建议 8~15")
        r = self._row(g, r, "缓冲时长(秒)",
                      ttk.Entry(g, textvariable=self._v("rec_buffer",
                                                        rec["buffer_seconds"]),
                                width=10), "可回溯窗口")
        r = self._row(g, r, "分辨率缩放",
                      ttk.Entry(g, textvariable=self._v("rec_scale",
                                                        rec["scale"]), width=10),
                      "0.5~1.0")
        r = self._row(g, r, "显示器编号",
                      ttk.Entry(g, textvariable=self._v("rec_monitor",
                                                        rec["monitor_index"]),
                                width=10), "1=主屏")

    def _reset_rec(self):
        for k, v in (("rec_fps", "10"), ("rec_buffer", "20"),
                     ("rec_scale", "0.75"), ("rec_monitor", "1")):
            if k in self._vars:
                self._vars[k].set(v)
        messagebox.showinfo("网安智盾", "录屏参数已恢复为推荐值，点「保存」生效。")

    # ---------------- 举报邮件 ----------------
    def _build_email(self):
        e = self.config.email
        f = self._tab("举报邮件", "可选：将举报草稿发往官方举报邮箱（如 jubao@12377.cn）。")
        g = self._group(f, "SMTP")
        r = 0
        r = self._row(g, r, "SMTP 服务器",
                      ttk.Entry(g, textvariable=self._v("smtp_server",
                                                        e["smtp_server"]), width=30))
        r = self._row(g, r, "SMTP 端口",
                      ttk.Entry(g, textvariable=self._v("smtp_port",
                                                        e["smtp_port"]), width=10))
        r = self._row(g, r, "发件人邮箱",
                      ttk.Entry(g, textvariable=self._v("sender",
                                                        e["sender"]), width=30))
        r = self._row(g, r, "发件人授权码",
                      ttk.Entry(g, textvariable=self._v("sender_password",
                                                        e["sender_password"]),
                                width=30, show="*"))
        r = self._row(g, r, "接收邮箱(官方举报)",
                      ttk.Entry(g, textvariable=self._v("receiver",
                                                        e["receiver"]), width=30),
                      "如 jubao@12377.cn")
        tk.Label(g, text="留空则仅生成本地举报草稿，不发邮件。",
                 bg="#eef2f7", fg="#9aa5b1",
                 font=("Microsoft YaHei", 8)).grid(
            row=r, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 0))

    # ---------------- 反伤 ----------------
    def _build_antistrike(self):
        a = self.config.anti_strike
        f = self._tab("反伤", "检测到攻击后弹出确认框，你确认才发起反伤（绝不自动举报）。")
        g = self._group(f, "反伤设置")
        r = 0
        r = self._row(g, r, "启用反伤（需手动确认）",
                      ttk.Checkbutton(g, variable=self._bool("anti_enabled",
                                                             a["enabled"])),
                      "程序绝不自动举报")
        r = self._row(g, r, "确认弹窗超时(秒)",
                      ttk.Entry(g, textvariable=self._v("anti_timeout",
                                                        a["confirm_timeout"]),
                                width=10), "0=不自动关闭")
        r = self._row(g, r, "反伤目标须含攻击性关键词",
                      ttk.Checkbutton(g,
                                      variable=self._bool("anti_req_kw",
                                                          a["require_attack_keyword"])))

    # ---------------- 标准弹药 ----------------
    def _build_ammo(self):
        f = self._tab("标准弹药", "默认对应条款，确认弹窗中可改。所有命途共享此格式。")
        g = self._group(f, "默认条款")
        tk.Label(g, text="默认对应条款（确认弹窗中可改）：",
                 bg="#eef2f7", fg="#1b2733",
                 font=("Microsoft YaHei", 9, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        self._clause = tk.Text(g, height=3, width=50,
                               font=("Microsoft YaHei", 9))
        self._clause.insert("1.0", self.config.default_clause)
        self._clause.grid(row=1, column=0, columnspan=3, sticky="ew",
                          padx=10, pady=4)
        tk.Label(g, text="标准弹药格式：目标账号 | 时间 | 违规内容 | 对应条款 | 证据附件",
                 bg="#eef2f7", fg="#9aa5b1",
                 font=("Microsoft YaHei", 8)).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=10, pady=4)

    # ---------------- 辅助 ----------------
    def _choose(self, var):
        p = filedialog.askdirectory()
        if p:
            var.set(p)

    # ---------------- 保存（逻辑与原版一致） ----------------
    def _save(self):
        c = self.config
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

        c.set("monitor", "keywords", ",".join(kws))
        c.set("monitor", "enable_screenshot", str(self._vars["enable_screenshot"].get()))
        c.set("monitor", "enable_recording", str(self._vars["enable_recording"].get()))
        c.set("monitor", "capture_delay", str(cap_d))
        c.set("monitor", "cooldown", str(cool))
        c.set("evidence", "save_path", self._vars["save_path"].get())
        c.set("evidence", "screenshot_format", self._vars["screenshot_format"].get())
        c.set("evidence", "max_screenshots", str(max_s))
        c.set("evidence", "encrypt", str(self._vars["encrypt"].get()))
        c.set("recorder", "enabled", str(self._vars["rec_enabled"].get()))
        c.set("recorder", "fps", str(fps))
        c.set("recorder", "buffer_seconds", str(buf))
        c.set("recorder", "scale", str(scale))
        c.set("recorder", "monitor_index", str(mon))
        c.set("email", "smtp_server", self._vars["smtp_server"].get())
        c.set("email", "smtp_port", str(port))
        c.set("email", "sender", self._vars["sender"].get())
        c.set("email", "sender_password", self._vars["sender_password"].get())
        c.set("email", "receiver", self._vars["receiver"].get())
        c.set("anti_strike", "enabled", str(self._vars["anti_enabled"].get()))
        c.set("anti_strike", "confirm_timeout", str(timeout))
        c.set("anti_strike", "require_attack_keyword",
              str(self._vars["anti_req_kw"].get()))
        c.set("standard_ammo", "default_clause",
              self._clause.get("1.0", "end").strip())

        if callable(self.on_applied):
            try:
                self.on_applied(c)
            except Exception as e:
                messagebox.showwarning("网安智盾", f"配置已保存，但热更新失败：{e}")
        messagebox.showinfo("网安智盾", "配置已保存并即时生效。")
        self.top.destroy()
