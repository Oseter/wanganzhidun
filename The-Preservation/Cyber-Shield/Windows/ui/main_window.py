"""主仪表盘窗口：网安智盾的「门面」。

常驻系统托盘，用户从托盘「显示主窗口」打开。展示：
    - 品牌头（盾牌 + 网安智盾 / 存护命途）
    - 状态药丸（监听 / 录屏 / 加密）
    - 本会话统计卡片（取证 / 证据 / 反伤）
    - 最近取证事件列表
    - 快捷操作按钮

关闭窗口 = 最小化到托盘（不退出）；只有「退出」按钮真正结束程序。
"""
import tkinter as tk
from tkinter import ttk

# 主题色（防御蓝 / 盾面蓝）
C_BG = "#eef2f7"
C_HEADER = "#1f4e79"
C_HEADER2 = "#2e6da4"
C_ACCENT = "#2178c8"
C_OK = "#2e9e5b"
C_WARN = "#c0392b"
C_GRAY = "#9aa5b1"
C_CARD = "#ffffff"
C_TEXT = "#1b2733"
C_SUB = "#5b6b7b"


class MainWindow:
    """构建并管理主仪表盘（根窗口即此窗口）。"""

    def __init__(self, root: tk.Tk, callbacks: dict):
        self.root = root
        self.cb = callbacks
        root.title("网安智盾 · WangAnZhiDun")
        root.geometry("640x560")
        root.minsize(560, 480)
        root.configure(bg=C_BG)
        root.protocol("WM_DELETE_WINDOW", self.cb.get("on_close", root.iconify))

        self._build_style()
        self._build_header()
        self._build_status()
        self._build_stats()
        self._build_events()
        self._build_actions()
        self._build_footer()

    # ---------------- 样式 ----------------
    def _build_style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TLabel", background=C_BG, foreground=C_TEXT,
                     font=("Microsoft YaHei", 10))
        st.configure("Title.TLabel", background=C_HEADER, foreground="white",
                     font=("Microsoft YaHei", 16, "bold"))
        st.configure("Sub.TLabel", background=C_HEADER, foreground="#cfe2f3",
                     font=("Microsoft YaHei", 9))
        st.configure("Card.TLabel", background=C_CARD, foreground=C_TEXT,
                     font=("Microsoft YaHei", 10))
        st.configure("Num.TLabel", background=C_CARD, foreground=C_ACCENT,
                     font=("Microsoft YaHei", 22, "bold"))
        st.configure("TButton", font=("Microsoft YaHei", 10))
        st.configure("Accent.TButton",
                     background=C_ACCENT, foreground="white",
                     font=("Microsoft YaHei", 10, "bold"))
        st.map("Accent.TButton", background=[("active", C_HEADER2)])

    # ---------------- 品牌头 ----------------
    def _build_header(self):
        f = tk.Frame(self.root, bg=C_HEADER)
        f.pack(fill="x")
        logo = self.cb.get("logo")
        if logo:
            lbl_img = tk.Label(f, image=logo, bg=C_HEADER)
            lbl_img.image = logo
            lbl_img.pack(side="left", padx=12, pady=10)
        tk.Label(f, text="网安智盾", style="Title.TLabel").pack(
            side="left", anchor="w", padx=(4, 0), pady=(8, 0))
        tk.Label(f, text="WangAnZhiDun · 存护命途 · 防打号 / 防点号 / 反伤",
                 style="Sub.TLabel").pack(side="left", anchor="w", padx=8, pady=(0, 10))

    # ---------------- 状态药丸 ----------------
    def _build_status(self):
        f = tk.Frame(self.root, bg=C_BG)
        f.pack(fill="x", padx=14, pady=(10, 0))
        self._pills = {}
        for key, label in (("monitor", "监听"), ("rec", "录屏"), ("enc", "加密")):
            pill = tk.Label(f, text=f"{label}：—", bg=C_GRAY, fg="white",
                            font=("Microsoft YaHei", 10, "bold"),
                            padx=12, pady=4, relief="flat")
            pill.pack(side="left", padx=4)
            self._pills[key] = (pill, label)
        self.set_running(True)
        self._set_pill("enc", True)

    def _set_pill(self, key: str, on: bool):
        pill, label = self._pills[key]
        if on:
            pill.configure(bg=C_OK, text=f"{label}：开")
        else:
            pill.configure(bg=C_WARN, text=f"{label}：关")

    def set_running(self, running: bool):
        self._running = running
        self._set_pill("monitor", running)
        self._set_pill("rec", running and self.cb.get("rec_enabled", True))

    def set_rec_enabled(self, enabled: bool):
        self.cb["rec_enabled"] = enabled
        self._set_pill("rec", self._running and enabled)

    # ---------------- 统计卡片 ----------------
    def _build_stats(self):
        f = tk.Frame(self.root, bg=C_BG)
        f.pack(fill="x", padx=14, pady=(10, 0))
        self._stat_vals = {}
        for key, label in (("forensics", "本次取证"),
                           ("evidence", "证据文件"),
                           ("anti", "反伤举报")):
            card = tk.Frame(f, bg=C_CARD, relief="groove", bd=1)
            card.pack(side="left", fill="both", expand=True, padx=4, ipady=8)
            num = tk.Label(card, text="0", style="Num.TLabel")
            num.pack(pady=(6, 0))
            tk.Label(card, text=label, style="Card.TLabel").pack()
            self._stat_vals[key] = num

    def set_stats(self, forensics: int, evidence: int, anti: int):
        self._stat_vals["forensics"].configure(text=str(forensics))
        self._stat_vals["evidence"].configure(text=str(evidence))
        self._stat_vals["anti"].configure(text=str(anti))

    # ---------------- 最近事件 ----------------
    def _build_events(self):
        f = tk.LabelFrame(self.root, text="最近取证事件", bg=C_BG,
                          fg=C_TEXT, font=("Microsoft YaHei", 10, "bold"))
        f.pack(fill="both", expand=True, padx=14, pady=(12, 0))
        f.configure(borderwidth=1, relief="groove")

        self._list = tk.Listbox(f, font=("Microsoft YaHei", 9),
                                bg="white", fg=C_TEXT, height=8,
                                selectbackground=C_ACCENT)
        sb = ttk.Scrollbar(f, orient="vertical", command=self._list.yview)
        self._list.configure(yscrollcommand=sb.set)
        self._list.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb.pack(side="right", fill="y", pady=6)

    def add_event(self, time_str: str, source: str, keyword: str):
        line = f"[{time_str}] {source} · 命中「{keyword}」"
        self._list.insert(0, line)
        if self._list.size() > 200:
            self._list.delete(200)

    def refresh_events(self, events: list):
        """用数据库记录整体刷新列表（窗口打开时调用）。"""
        self._list.delete(0, "end")
        for ev in events:
            ts = (ev.get("timestamp") or "")[:19].replace("T", " ")
            src = ev.get("source_app") or "未知"
            kw = ev.get("keyword") or "命中"
            self._list.insert("end", f"[{ts}] {src} · 命中「{kw}」")

    # ---------------- 快捷操作 ----------------
    def _build_actions(self):
        f = tk.Frame(self.root, bg=C_BG)
        f.pack(fill="x", padx=14, pady=(12, 0))
        acts = [
            ("设置", self.cb.get("on_settings"), False),
            ("证据目录", self.cb.get("on_open_evidence"), False),
            ("暂停/继续", self.cb.get("on_toggle"), False),
            ("测试取证", self.cb.get("on_test"), True),
            ("退出", self.cb.get("on_quit"), True),
        ]
        for label, cmd, danger in acts:
            if cmd is None:
                continue
            btn = ttk.Button(f, text=label, command=cmd,
                             style="Accent.TButton" if danger else "TButton")
            btn.pack(side="left", padx=4, ipadx=4)

    # ---------------- 脚注 ----------------
    def _build_footer(self):
        tk.Label(
            self.root,
            text="合法使用：仅记录针对本人的恶意攻击，证据真实，经官方合规渠道举报；不伪造、不自动举报。",
            bg=C_BG, fg=C_SUB, font=("Microsoft YaHei", 8),
        ).pack(side="bottom", fill="x", pady=(6, 8))
