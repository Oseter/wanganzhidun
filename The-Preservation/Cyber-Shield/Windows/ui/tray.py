"""系统托盘：常驻后台，右键菜单控制。

菜单项：
    显示主窗口  — 打开/聚焦主仪表盘
    打开证据目录 — 资源管理器打开 evidence/
    设置        — 打开配置窗口
    暂停/继续   — 切换监听（标签随状态变化）
    退出        — 停止并退出

盾牌图标由 icons 模块纯代码绘制，不依赖外部资源。
"""
import os
import webbrowser
from typing import Callable, Optional

from ui.icons import tray_icon


class TrayApp:
    """pystray 系统托盘封装。"""

    def __init__(self, evidence_dir: str, ui: Optional[Callable] = None,
                 on_settings: Callable = None, on_open_evidence: Callable = None,
                 on_toggle: Callable[[bool], None] = None, on_quit: Callable = None):
        self.evidence_dir = evidence_dir
        self.ui = ui
        self.on_settings = on_settings
        self.on_open_evidence = on_open_evidence
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self._running = True
        self._icon = None
        self._thread = None

    def _build_menu(self):
        import pystray
        from pystray import Menu, MenuItem

        def open_evidence(icon, item):
            if os.name == "nt":
                os.startfile(self.evidence_dir)
            else:
                os.system(f'xdg-open "{self.evidence_dir}"')

        def show_main(icon, item):
            if self.ui:
                self.ui.show()

        def settings(icon, item):
            if self.on_settings:
                self.on_settings()

        def toggle(icon, item):
            self._running = not self._running
            if self.on_toggle:
                self.on_toggle(self._running)
            icon.update_menu()

        def quit_app(icon, item):
            if self.on_quit:
                self.on_quit()
            icon.stop()

        return Menu(
            MenuItem("显示主窗口", show_main),
            MenuItem("打开证据目录", open_evidence),
            MenuItem("设置", settings),
            MenuItem(lambda i, m: "继续监听" if not self._running else "暂停监听",
                     toggle),
            Menu.SEPARATOR,
            MenuItem("退出", quit_app),
        )

    def _run(self):
        import pystray

        self._icon = pystray.Icon(
            "WangAnZhiDun", tray_icon(64), "网安智盾", self._build_menu()
        )
        self._icon.run()

    def start(self):
        self._thread = __import__("threading").Thread(
            target=self._run, daemon=True)
        self._thread.start()

    def notify(self, title: str, message: str):
        if self._icon:
            self._icon.notify(message, title)

    def set_running(self, running: bool):
        self._running = running
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass
