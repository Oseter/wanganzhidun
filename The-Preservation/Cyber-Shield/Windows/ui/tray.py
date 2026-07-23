import os
from typing import Callable, Optional

from ui.icons import tray_icon


class TrayApp:
    def __init__(self, evidence_dir: str, ui: Optional[Callable] = None,
                 on_settings: Callable = None, on_open_evidence: Callable = None,
                 on_toggle: Callable = None, on_quit: Callable = None,
                 on_test: Callable = None, on_about: Callable = None,
                 on_reload: Callable = None):
        self.evidence_dir = evidence_dir
        self.ui = ui
        self.on_settings = on_settings
        self.on_open_evidence = on_open_evidence
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.on_test = on_test
        self.on_about = on_about
        self.on_reload = on_reload
        self._running = True
        self._icon = None
        self._thread = None

    def _build_menu(self):
        import pystray
        from pystray import Menu, MenuItem

        items = [
            MenuItem("显示主窗口", lambda i, it: self.ui and self.ui.show()),
            MenuItem("打开证据目录", lambda i, it: os.startfile(self.evidence_dir) if os.name == "nt" else os.system(f'xdg-open "{self.evidence_dir}"')),
            MenuItem("设置", lambda i, it: self.on_settings() if self.on_settings else None),
        ]
        if self.on_test:
            items.append(MenuItem("立即测试取证", lambda i, it: self.on_test()))
        if self.on_reload:
            items.append(MenuItem("重载配置", lambda i, it: self.on_reload()))
        items.append(MenuItem(
            lambda i, m: "继续监听" if not self._running else "暂停监听",
            lambda i, it: self._toggle(i, it)))
        items.append(Menu.SEPARATOR)
        if self.on_about:
            items.append(MenuItem("关于网安智盾", lambda i, it: self.on_about()))
        items.append(MenuItem("退出", lambda i, it: self._quit(it)))
        return Menu(*items)

    def _toggle(self, icon, item):
        self._running = not self._running
        if self.on_toggle:
            self.on_toggle()
        icon.update_menu()

    def _quit(self, icon):
        if self.on_quit:
            self.on_quit()
        icon.stop()

    def _run(self):
        import pystray
        try:
            icon_img = tray_icon(64, active=self._running)
        except Exception:
            from PIL import Image
            icon_img = Image.new("RGBA", (64, 64), (33, 120, 200, 255))
        try:
            self._icon = pystray.Icon("WangAnZhiDun", icon_img, "网安智盾", self._build_menu())
            self._icon.run()
        except Exception:
            pass

    def start(self):
        import threading
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def notify(self, title: str, message: str):
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def set_running(self, running: bool):
        self._running = running
        if self._icon:
            try:
                self._icon.icon = tray_icon(64, active=running)
                self._icon.update_menu()
            except Exception:
                pass
