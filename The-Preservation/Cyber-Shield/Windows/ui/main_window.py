import tkinter as tk
from tkinter import ttk

C_BG = "#eef2f7"
C_PANEL = "#f7f9fc"
C_HEADER = "#163a5f"
C_HEADER2 = "#1f4e79"
C_ACCENT = "#2178c8"
C_OK = "#27ae60"
C_WARN = "#e74c3c"
C_GRAY = "#95a5a6"
C_CARD = "#ffffff"
C_TEXT = "#1b2733"
C_SUB = "#5b6b7b"
C_LINE = "#d7dee8"

KIND_COLOR = {
    "forensics": "#2178c8",
    "anti": "#27ae60",
    "test": "#95a5a6",
    "info": "#8e44ad",
    "anti_tag": "#e67e22",
    "report": "#c0392b",
}
KIND_TAG = {
    "forensics": "取证",
    "anti": "反伤",
    "test": "测试",
    "info": "提示",
    "anti_tag": "防点号",
    "report": "防打号",
}


class MainWindow:
    def __init__(self, root: tk.Tk, callbacks: dict):
        self.root = root
        self.cb = callbacks
        root.title("网安智盾 · WangAnZhiDun")
        root.geometry("720x640")
        root.minsize(600, 520)
        root.configure(bg=C_BG)
        root.protocol("WM_DELETE_WINDOW", self.cb.get("on_close", root.iconify))

        self._running = True
        self._rec_enabled = True
        self._build_style()
        self._build_header()
        self._build_statusbar()
        self._build_stats()
        self._build_events()
        self._build_actions()
        self._build_footer()

    def _build_style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TLabel", background=C_BG, foreground=C_TEXT, font=("Microsoft YaHei", 10))
        st.configure("Title.TLabel", background=C_HEADER, foreground="white", font=("Microsoft YaHei", 17, "bold"))
        st.configure("Sub.TLabel", background=C_HEADER, foreground="#cfe2f3", font=("Microsoft YaHei", 9))
        st.configure("CardTitle.TLabel", background=C_CARD, foreground=C_SUB, font=("Microsoft YaHei", 9))
        st.configure("Num.TLabel", background=C_CARD, foreground=C_ACCENT, font=("Microsoft YaHei", 24, "bold"))
        st.configure("TButton", font=("Microsoft YaHei", 10))
        st.configure("Accent.TButton", background=C_ACCENT, foreground="white", font=("Microsoft YaHei", 10, "bold"))
        st.map("Accent.TButton", background=[("active", C_HEADER2)])
        st.configure("Ghost.TButton", background=C_PANEL, foreground=C_TEXT, font=("Microsoft YaHei", 10))
        st.map("Ghost.TButton", background=[("active", "#e3e9f2")])
        st.configure("Danger.TButton", background="#fdecea", foreground=C_WARN, font=("Microsoft YaHei", 10, "bold"))
        st.map("Danger.TButton", background=[("active", "#f9d5d0")])

    def _build_header(self):
        f = tk.Frame(self.root, bg=C_HEADER)
        f.pack(fill="x")
        logo = self.cb.get("logo")
        if logo:
            lbl_img = tk.Label(f, image=logo, bg=C_HEADER)
            lbl_img.image = logo
            lbl_img.pack(side="left", padx=14, pady=12)
        titles = tk.Frame(f, bg=C_HEADER)
        titles.pack(side="left", anchor="w", pady=(10, 0))
        ttk.Label(titles, text="网安智盾", style="Title.TLabel").pack(anchor="w")
        ttk.Label(titles, text="WangAnZhiDun · 存护命途 · 防打号 / 防点号 / 反伤",
                 style="Sub.TLabel").pack(anchor="w", pady=(2, 0))
        self._uptime_var = tk.StringVar(value="运行 00:00")
        tk.Label(f, textvariable=self._uptime_var, bg=C_HEADER, fg="#cfe2f3",
                 font=("Microsoft YaHei", 9)).pack(side="right", padx=16, pady=14)

    def _build_statusbar(self):
        f = tk.Frame(self.root, bg=C_PANEL, relief="flat", bd=0)
        f.pack(fill="x", padx=14, pady=(12, 0))
        f.configure(height=40)
        self._state_var = tk.StringVar(value="运行中")
        self._state_lbl = tk.Label(f, textvariable=self._state_var,
                                   bg=C_PANEL, fg=C_OK,
                                   font=("Microsoft YaHei", 13, "bold"))
        self._state_lbl.pack(side="left", padx=10, pady=8)
        self._pills = {}
        for key, label in (("monitor", "监听"), ("rec", "录屏"), ("enc", "加密"), ("obs", "OBS")):
            pill = tk.Label(f, text=f"{label}：—", bg=C_GRAY, fg="white",
                            font=("Microsoft YaHei", 10, "bold"),
                            padx=12, pady=4, relief="flat")
            pill.pack(side="left", padx=4)
            self._pills[key] = (pill, label)
        self.set_running(True)

    def _set_pill(self, key: str, on: bool, color: str = None):
        pill, label = self._pills[key]
        bg = color or (C_OK if on else C_WARN)
        pill.configure(bg=bg, text=f"{label}：{'开' if on else '关'}")

    def set_running(self, running: bool):
        self._running = running
        self._state_var.set("运行中" if running else "已暂停")
        self._state_lbl.configure(fg=C_OK if running else C_WARN)
        self._set_pill("monitor", running)
        self._set_pill("rec", running and self._rec_enabled)

    def set_rec_enabled(self, enabled: bool):
        self._rec_enabled = enabled
        self._set_pill("rec", self._running and enabled)

    def set_obs_enabled(self, enabled: bool):
        self._set_pill("obs", enabled)

    def set_enc_enabled(self, enabled: bool):
        self._set_pill("enc", enabled)

    def set_uptime(self, seconds: int):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            self._uptime_var.set(f"运行 {h:02d}:{m:02d}:{s:02d}")
        else:
            self._uptime_var.set(f"运行 {m:02d}:{s:02d}")

    def _build_stats(self):
        f = tk.Frame(self.root, bg=C_BG)
        f.pack(fill="x", padx=14, pady=(12, 0))
        self._stat_vals = {}
        specs = (
            ("forensics", "本次取证", "截图 / 录像 / 归档"),
            ("evidence", "证据文件", "截图 + 录像计数"),
            ("anti", "反伤举报", "已确认并发起"),
            ("anti_tag", "防点号拦截", "异常检测次数"),
        )
        for key, label, sub in specs:
            card = tk.Frame(f, bg=C_CARD, relief="flat", bd=1,
                            highlightbackground=C_LINE, highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
            num = ttk.Label(card, text="0", style="Num.TLabel")
            num.pack(pady=(8, 0))
            ttk.Label(card, text=label, style="CardTitle.TLabel").pack()
            tk.Label(card, text=sub, bg=C_CARD, fg=C_GRAY,
                     font=("Microsoft YaHei", 8)).pack()
            self._stat_vals[key] = num

    def set_stats(self, forensics: int, evidence: int, anti: int, anti_tag: int = 0):
        self._stat_vals["forensics"].configure(text=str(forensics))
        self._stat_vals["evidence"].configure(text=str(evidence))
        self._stat_vals["anti"].configure(text=str(anti))
        self._stat_vals["anti_tag"].configure(text=str(anti_tag))

    def _build_events(self):
        outer = tk.Frame(self.root, bg=C_BG)
        outer.pack(fill="both", expand=True, padx=14, pady=(12, 0))
        f = tk.LabelFrame(outer, text="最近事件", bg=C_BG, fg=C_TEXT,
                          font=("Microsoft YaHei", 10, "bold"))
        f.configure(borderwidth=1, relief="groove",
                    highlightbackground=C_LINE, highlightthickness=1)
        f.pack(fill="both", expand=True, padx=0, pady=0)

        self._list = tk.Listbox(f, font=("Microsoft YaHei", 9),
                                bg="white", fg=C_TEXT, height=9,
                                selectbackground=C_ACCENT, activestyle="none",
                                relief="flat", bd=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=self._list.yview)
        self._list.configure(yscrollcommand=sb.set)
        self._list.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        sb.pack(side="right", fill="y", pady=8)

        self._empty_var = tk.StringVar(value="暂无事件。命中关键词将自动在此列出。")
        self._empty = tk.Label(outer, textvariable=self._empty_var, bg=C_BG,
                               fg=C_GRAY, font=("Microsoft YaHei", 9))
        self._empty.place(relx=0.5, rely=0.5, anchor="center")
        self._empty.lift()

    def _hide_empty(self):
        if self._empty.winfo_viewable():
            self._empty.place_forget()

    def add_event(self, time_str: str, source: str, keyword: str, kind: str = "forensics"):
        self._hide_empty()
        color = KIND_COLOR.get(kind, C_TEXT)
        label = KIND_TAG.get(kind, "取证")
        line = f"[{label}] [{time_str}] {source} · {keyword}"
        self._list.insert(0, line)
        self._list.itemconfig(0, fg=color)
        if self._list.size() > 200:
            self._list.delete(200)

    def refresh_events(self, events: list):
        self._list.delete(0, "end")
        if not events:
            self._empty_var.set("暂无事件。")
            self._empty.place(relx=0.5, rely=0.5, anchor="center")
            self._empty.lift()
            return
        self._hide_empty()
        for idx, ev in enumerate(events):
            ts = (ev.get("timestamp") or "")[:19].replace("T", " ")
            src = ev.get("source_app") or "未知"
            kw = ev.get("keyword") or "命中"
            kind = ev.get("event_type", "forensics")
            color = KIND_COLOR.get(kind, C_TEXT)
            label = KIND_TAG.get(kind, "取证")
            self._list.insert("end", f"[{label}] [{ts}] {src} · {kw}")
            self._list.itemconfig(idx, fg=color)

    def _build_actions(self):
        fg = tk.Frame(self.root, bg=C_BG)
        fg.pack(fill="x", padx=14, pady=(12, 0))
        main = [
            ("设置", self.cb.get("on_settings")),
            ("证据目录", self.cb.get("on_open_evidence")),
            ("暂停/继续", self.cb.get("on_toggle")),
            ("测试取证", self.cb.get("on_test")),
        ]
        for label, cmd in main:
            if cmd is None:
                continue
            ttk.Button(fg, text=label, command=cmd, style="Accent.TButton").pack(
                side="left", padx=4, ipadx=6)
        for label, key in (("证据库", "on_view_db"), ("关于", "on_about")):
            cmd = self.cb.get(key)
            if cmd is not None:
                ttk.Button(fg, text=label, command=cmd, style="Ghost.TButton").pack(
                    side="left", padx=4, ipadx=6)
        danger = self.cb.get("on_quit")
        if danger is not None:
            ttk.Button(fg, text="退出", command=danger, style="Danger.TButton").pack(
                side="right", padx=4, ipadx=6)

    def _build_footer(self):
        tk.Label(
            self.root,
            text="合法使用：仅记录针对本人的恶意攻击，证据真实，经官方合规渠道举报；不伪造、不自动举报。",
            bg=C_BG, fg=C_SUB, font=("Microsoft YaHei", 8),
        ).pack(side="bottom", fill="x", pady=(6, 8))
