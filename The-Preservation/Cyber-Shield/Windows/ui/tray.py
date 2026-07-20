"""系统托盘（UI 改进版）：常驻后台，右键菜单控制。

相对旧版改进：
    - 菜单增强：新增「立即测试取证 / 关于 / 重载配置」（回调缺失则自动隐藏，向后兼容）；
    - 暂停态图标变灰：set_running(False) 时切换为灰色盾牌，状态一眼可见；
    - 悬停提示显示运行状态（pystray 标题）。

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
                 on_toggle: Callable[[bool], None] = None, on_quit: Callable = None,
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

        def test_now(icon, item):
            if self.on_test:
                self.on_test()

        def about(icon, item):
            if self.on_about:
                self.on_about()

        def reload_cfg(icon, item):
            if self.on_reload:
                self.on_reload()

        def toggle(icon, item):
            self._running = not self._running
            if self.on_toggle:
                self.on_toggle(self._running)
            icon.update_menu()

        def quit_app(icon, item):
            if self.on_quit:
                self.on_quit()
            icon.stop()

        items = [
            MenuItem("显示主窗口", show_main),
            MenuItem("打开证据目录", open_evidence),
            MenuItem("设置", settings),
        ]
        if self.on_test is not None:
            items.append(MenuItem("立即测试取证", test_now))
        if self.on_reload is not None:
            items.append(MenuItem("重载配置", reload_cfg))
        items.append(MenuItem(
            lambda i, m: "继续监听" if not self._running else "暂停监听", toggle))
        items.append(Menu.SEPARATOR)
        if self.on_about is not None:
            items.append(MenuItem("关于网安智盾", about))
        items.append(MenuItem("退出", quit_app))
        return Menu(*items)

    def _run(self):
        import pystray

        self._icon = pystray.Icon(
            "WangAnZhiDun",
            tray_icon(64, active=self._running),
            "网安智盾",
            self._build_menu(),
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
                self._icon.icon = tray_icon(64, active=running)
            except Exception:
                pass
            try:
                self._icon.update_menu()
            except Exception:
                pass
