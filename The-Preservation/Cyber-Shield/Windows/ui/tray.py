"""系统托盘：常驻后台，右键菜单控制。

菜单项：
    显示状态    — 弹出当前监控状态
    打开证据目录 — 资源管理器打开 evidence/
    设置        — 打开配置窗口
    暂停/继续   — 切换监听
    退出        — 停止并退出
"""
import os
import threading
import webbrowser
from typing import Callable


class TrayApp:
    """pystray 系统托盘封装。"""

    def __init__(self, evidence_dir: str, on_settings: Callable,
                 on_toggle: Callable[[bool], None], on_quit: Callable):
        self.evidence_dir = evidence_dir
        self.on_settings = on_settings
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self._running = True
        self._icon = None
        self._thread = None

    def _build_menu(self):
        import pystray
        from pystray import Menu, MenuItem

        def open_evidence(icon, item):
            os.startfile(self.evidence_dir) if os.name == "nt" \
                else os.system(f'xdg-open "{self.evidence_dir}"')

        def toggle(icon, item):
            self._running = not self._running
            self.on_toggle(self._running)
            icon.update_menu()

        def quit_app(icon, item):
            self.on_quit()
            icon.stop()

        return Menu(
            MenuItem("状态", lambda i, m: None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("打开证据目录", open_evidence),
            MenuItem("设置", lambda i, m: self.on_settings()),
            MenuItem("暂停/继续", toggle),
            Menu.SEPARATOR,
            MenuItem("退出", quit_app),
        )

    def _run(self):
        import pystray
        from PIL import Image, ImageDraw

        # 生成一个简易盾牌图标（无需外部资源）
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([8, 8, 56, 56], fill=(33, 120, 200, 255))
        d.rectangle([24, 24, 40, 48], fill=(255, 255, 255, 255))

        self._icon = pystray.Icon(
            "WangAnZhiDun", img, "网安智盾", self._build_menu()
        )
        self._icon.run()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def notify(self, title: str, message: str):
        if self._icon:
            self._icon.notify(message, title)
