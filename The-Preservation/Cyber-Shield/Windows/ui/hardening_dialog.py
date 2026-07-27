import os
import tkinter as tk
from tkinter import ttk, messagebox
from core.config import ConfigManager

HARDENING_ITEMS = [
    ("device_lock", "设备锁", "检查是否已开启设备锁/登录保护"),
    ("verified", "实名认证", "确认已完成实名认证"),
    ("multi_factor", "多因子认证", "开启二次验证/多因子认证"),
    ("login_protect", "登录保护", "开启异地登录保护"),
    ("device_clean", "登录设备管理", "清理不常用登录设备"),
    ("strong_password", "密码强度", "检查密码是否为高强度唯一密码"),
]


class HardeningDialog:
    def __init__(self, parent: tk.Tk, cfg: ConfigManager, on_done=None):
        self.cfg = cfg
        self.on_done = on_done
        self.vars = {}

        self.top = tk.Toplevel(parent)
        self.top.title("网安智盾 · 账号加固")
        self.top.geometry("520x460")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg="#eef2f7")

        banner = tk.Label(self.top, text="首次使用建议先完成账号加固，提升账号抗性，让对方打不动你的号。",
                          bg="#d4e6f1", fg="#1a5276",
                          font=("Microsoft YaHei", 9), anchor="w",
                          padx=14, pady=10, relief="flat")
        banner.pack(fill="x", padx=10, pady=(10, 4))

        g = tk.LabelFrame(self.top, text="加固清单", bg="#eef2f7", fg="#1b2733",
                          font=("Microsoft YaHei", 10, "bold"))
        g.pack(fill="both", expand=True, padx=14, pady=8)

        for idx, (key, label, hint) in enumerate(HARDENING_ITEMS):
            current = self.cfg.get_bool("hardening", key, False)
            var = tk.BooleanVar(value=current)
            self.vars[key] = var
            cb = ttk.Checkbutton(g, text=label, variable=var)
            cb.grid(row=idx, column=0, sticky="w", padx=14, pady=6)
            tk.Label(g, text=hint, bg="#eef2f7", fg="#7f8c8d",
                     font=("Microsoft YaHei", 8)).grid(
                row=idx, column=1, sticky="w", padx=6)

        bf = tk.Frame(self.top, bg="#eef2f7")
        bf.pack(fill="x", pady=(4, 12))
        ttk.Button(bf, text="保存", command=self._save,
                   style="Accent.TButton").pack(side="right", padx=10)
        ttk.Button(bf, text="关闭", command=self.top.destroy).pack(side="right")

    def show(self):
        self.top.deiconify()
        self.top.lift()

    def _save(self):
        for key, var in self.vars.items():
            self.cfg.set("hardening", key, str(var.get()).lower())
        if callable(self.on_done):
            try:
                self.on_done()
            except Exception:
                pass
        messagebox.showinfo("网安智盾", "加固状态已保存。可在设置中重新打开。")
        self.top.destroy()


def show_if_needed(parent: tk.Tk, cfg_path: str, on_done=None):
    cfg = ConfigManager(cfg_path)
    done = all(cfg.get_bool("hardening", key, False) for key, _, _ in HARDENING_ITEMS)
    if done:
        return
    dlg = HardeningDialog(parent, cfg, on_done=on_done)
    dlg.show()
