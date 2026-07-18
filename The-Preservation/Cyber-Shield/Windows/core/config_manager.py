"""配置管理：读取 / 写入 config.ini。

普通用户改 config.ini 即可调整行为，无需碰代码。
"""
import configparser
import os
from typing import List


class ConfigManager:
    """封装 config.ini 的读写，提供类型化访问接口。"""

    DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")

    def __init__(self, path: str = None):
        self.path = os.path.abspath(path or self.DEFAULT_PATH)
        self._parser = configparser.ConfigParser()
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"配置文件不存在：{self.path}")
        self._parser.read(self.path, encoding="utf-8")

    # ---------- 通用读取 ----------
    def get(self, section: str, key: str, fallback=None):
        return self._parser.get(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback=False) -> bool:
        return self._parser.getboolean(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback=0) -> int:
        try:
            return self._parser.getint(section, key, fallback=fallback)
        except ValueError:
            return fallback

    # ---------- 监听相关 ----------
    @property
    def keywords(self) -> List[str]:
        raw = self.get("monitor", "keywords", fallback="")
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def enable_screenshot(self) -> bool:
        return self.get_bool("monitor", "enable_screenshot", True)

    @property
    def enable_recording(self) -> bool:
        return self.get_bool("monitor", "enable_recording", True)

    @property
    def capture_delay(self) -> int:
        return self.get_int("monitor", "capture_delay", 1)

    @property
    def cooldown(self) -> int:
        return self.get_int("monitor", "cooldown", 30)

    # ---------- 证据相关 ----------
    @property
    def save_path(self) -> str:
        p = self.get("evidence", "save_path", fallback="")
        if not p:
            p = os.path.join(os.path.dirname(self.path), "evidence")
        return os.path.abspath(p)

    @property
    def screenshot_format(self) -> str:
        return self.get("evidence", "screenshot_format", fallback="png")

    @property
    def max_screenshots(self) -> int:
        return self.get_int("evidence", "max_screenshots", 3)

    @property
    def encrypt(self) -> bool:
        return self.get_bool("evidence", "encrypt", True)

    # ---------- 自带录屏（无外部应用依赖） ----------
    @property
    def recorder(self) -> dict:
        return {
            "enabled": self.get_bool("recorder", "enabled", True),
            "fps": self.get_int("recorder", "fps", 10),
            "buffer_seconds": self.get_int("recorder", "buffer_seconds", 30),
            "scale": float(self.get("recorder", "scale", "0.75")),
            "monitor_index": self.get_int("recorder", "monitor_index", 1),
        }

    # ---------- 邮件 ----------
    @property
    def email(self) -> dict:
        return {
            "smtp_server": self.get("email", "smtp_server", ""),
            "smtp_port": self.get_int("email", "smtp_port", 587),
            "sender": self.get("email", "sender", ""),
            "sender_password": self.get("email", "sender_password", ""),
            "receiver": self.get("email", "receiver", "jubao@12377.cn"),
        }

    # ---------- 反伤 ----------
    @property
    def anti_strike(self) -> dict:
        return {
            "enabled": self.get_bool("anti_strike", "enabled", False),
            "confirm_timeout": self.get_int("anti_strike", "confirm_timeout", 30),
            "require_attack_keyword": self.get_bool(
                "anti_strike", "require_attack_keyword", True
            ),
        }

    @property
    def default_clause(self) -> str:
        return self.get(
            "standard_ammo",
            "default_clause",
            "《网络安全法》第十二条 / 平台用户协议-骚扰恶意举报",
        )

    # ---------- 写入 ----------
    def set(self, section: str, key: str, value):
        if not self._parser.has_section(section):
            self._parser.add_section(section)
        self._parser.set(section, key, str(value))
        with open(self.path, "w", encoding="utf-8") as f:
            self._parser.write(f)
