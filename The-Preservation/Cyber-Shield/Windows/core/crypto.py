"""本地证据加密：对截图 / 录像 / 元数据做 AES 加密，防止证据被窃取篡改。

密钥由用户密码派生（PBKDF2 + Fernet）。零代码用户首次运行时会引导设置密码；
未设置密码则使用设备级默认密钥（仍优于明文）。
"""
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EvidenceCrypto:
    """证据文件加解密工具。"""

    SALT_FILE = "crypto_salt.bin"
    KEY_FILE = "crypto_key.bin"

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        os.makedirs(work_dir, exist_ok=True)
        self._key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        key_path = os.path.join(self.work_dir, self.KEY_FILE)
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        # 首次运行：生成随机密钥（相当于设备级默认保护）
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        # 密钥文件仅当前用户可读
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return key

    def set_user_password(self, password: str):
        """用用户密码重新派生密钥（可选，提升安全性）。"""
        salt_path = os.path.join(self.work_dir, self.SALT_FILE)
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                salt = f.read()
        else:
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000
        )
        derived = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        with open(os.path.join(self.work_dir, self.KEY_FILE), "wb") as f:
            f.write(derived)
        self._key = derived

    def encrypt_file(self, src_path: str, dst_path: str = None) -> str:
        """加密文件，默认输出为 src_path + '.enc'。"""
        if dst_path is None:
            dst_path = src_path + ".enc"
        f = Fernet(self._key)
        with open(src_path, "rb") as fp:
            data = fp.read()
        token = f.encrypt(data)
        with open(dst_path, "wb") as fp:
            fp.write(token)
        return dst_path

    def decrypt_file(self, src_path: str, dst_path: str = None) -> str:
        if dst_path is None:
            dst_path = src_path[:-4] if src_path.endswith(".enc") else src_path + ".dec"
        f = Fernet(self._key)
        with open(src_path, "rb") as fp:
            token = fp.read()
        data = f.decrypt(token)
        with open(dst_path, "wb") as fp:
            fp.write(data)
        return dst_path
