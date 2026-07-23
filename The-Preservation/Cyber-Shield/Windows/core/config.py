import configparser
import os
import sys
from typing import List, Dict, Optional


def _find_config() -> str:
    candidates = [
        os.path.join(os.path.dirname(sys.executable), "config.ini"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini"),
        os.path.join(os.getcwd(), "config.ini"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])


class ConfigManager:
    def __init__(self, path: Optional[str] = None):
        self.path = os.path.abspath(path or _find_config())
        self._parser = configparser.ConfigParser()
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"config.ini 不存在：{self.path}")
        self._parser.read(self.path, encoding="utf-8")

    # --- 通用 ---
    def get(self, section: str, key: str, fallback=None) -> str:
        return self._parser.get(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback=False) -> bool:
        return self._parser.getboolean(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback=0) -> int:
        try:
            return self._parser.getint(section, key, fallback=fallback)
        except ValueError:
            return fallback

    def get_float(self, section: str, key: str, fallback=0.0) -> float:
        try:
            return self._parser.getfloat(section, key, fallback=fallback)
        except ValueError:
            return fallback

    def set(self, section: str, key: str, value):
        if not self._parser.has_section(section):
            self._parser.add_section(section)
        self._parser.set(section, key, str(value))
        with open(self.path, "w", encoding="utf-8") as f:
            self._parser.write(f)

    # --- 监测 ---
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

    # --- 证据 ---
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

    # --- OBS 录屏 ---
    @property
    def obs(self) -> dict:
        return {
            "enabled": self.get_bool("obs", "enabled", False),
            "host": self.get("obs", "host", "127.0.0.1"),
            "port": self.get_int("obs", "port", 4455),
            "password": self.get("obs", "password", ""),
            "replay_buffer_seconds": self.get_int("obs", "replay_buffer_seconds", 60),
        }

    # --- 反伤通道 ---
    @property
    def channels(self) -> dict:
        return {
            "web_12377": self.get_bool("channels", "web_12377", True),
            "email_12377": self.get_bool("channels", "email_12377", True),
            "guard": self.get_bool("channels", "guard", True),
            "provincial": self.get_bool("channels", "provincial", False),
            "miit": self.get_bool("channels", "miit", False),
            "url_12377": self.get("channels", "url_12377", "https://www.12377.cn/"),
            "url_guard": self.get("channels", "url_guard", "https://110.qq.com/"),
            "email_receiver": self.get("channels", "email_receiver", "jubao@12377.cn"),
            "copy_ammo": self.get_bool("channels", "copy_ammo", True),
        }

    # --- SMTP ---
    @property
    def email(self) -> dict:
        return {
            "smtp_server": self.get("email", "smtp_server", ""),
            "smtp_port": self.get_int("email", "smtp_port", 587),
            "sender": self.get("email", "sender", ""),
            "sender_password": self.get("email", "sender_password", ""),
        }

    # --- 反伤 ---
    @property
    def anti_strike(self) -> dict:
        return {
            "enabled": self.get_bool("anti_strike", "enabled", False),
            "confirm_timeout": self.get_int("anti_strike", "confirm_timeout", 30),
            "require_attack_keyword": self.get_bool("anti_strike", "require_attack_keyword", True),
        }

    # --- 标准弹药 ---
    @property
    def default_clause(self) -> str:
        return self.get("standard_ammo", "default_clause",
                        "《网络安全法》第十二条 / 平台用户协议-骚扰恶意举报")

    # --- 防点号 ---
    @property
    def anti_tag(self) -> dict:
        return {
            "enabled": self.get_bool("anti_tag", "enabled", True),
            "friend_request_threshold": self.get_int("anti_tag", "friend_request_threshold", 20),
            "friend_request_window": self.get_int("anti_tag", "friend_request_window", 300),
            "temp_session_threshold": self.get_int("anti_tag", "temp_session_threshold", 30),
            "temp_session_window": self.get_int("anti_tag", "temp_session_window", 300),
            "group_invite_threshold": self.get_int("anti_tag", "group_invite_threshold", 10),
            "group_invite_window": self.get_int("anti_tag", "group_invite_window", 300),
            "auto_freeze": self.get_bool("anti_tag", "auto_freeze", False),
        }

    # --- CWAS 协同 ---
    @property
    def cwas(self) -> dict:
        return {
            "enabled": self.get_bool("cwas", "enabled", False),
            "endpoint": self.get("cwas", "endpoint", ""),
            "api_key": self.get("cwas", "api_key", ""),
        }
