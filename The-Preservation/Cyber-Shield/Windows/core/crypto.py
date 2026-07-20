"""本地证据加密：对截图 / 录像 / 元数据做 AES 加密，防止证据被窃取篡改。

密钥由用户密码派生（PBKDF2 + Fernet）。零代码用户首次运行时会引导设置密码；
未设置密码则使用设备级默认密钥（仍优于明文）。

cryptography 依赖在 PyInstaller 打包后可能因环境问题无法导入，
因此全部改为延迟加载，导入失败时降级为明文存储（不影响程序启动）。
"""
import base64
import os


# 延迟导入，打包后 cryptography 的 _rust.pyd 或 OpenSSL DLL 可能因
# 杀软拦截 / 缺少 VC 运行时等原因无法加载，顶层 import 会阻止整个程序启动。
_Fernet = None
_hashes = None
_PBKDF2HMAC = None
_crypto_available = None


def _ensure_crypto():
    global _Fernet, _hashes, _PBKDF2HMAC, _crypto_available
    if _crypto_available is not None:
        return _crypto_available
    try:
        from cryptography.fernet import Fernet as _F
        from cryptography.hazmat.primitives import hashes as _h
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as _P
        _Fernet = _F
        _hashes = _h
        _PBKDF2HMAC = _P
        _crypto_available = True
    except Exception:
        _crypto_available = False
    return _crypto_available


class EvidenceCrypto:
    """证据文件加解密工具。cryptography 不可用时降级为明文（不加密）。"""

    SALT_FILE = "crypto_salt.bin"
    KEY_FILE = "crypto_key.bin"

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self._available = _ensure_crypto()
        os.makedirs(work_dir, exist_ok=True)
        self._key = self._load_or_create_key() if self._available else b""

    @property
    def available(self) -> bool:
        return self._available

    def _load_or_create_key(self) -> bytes:
        key_path = os.path.join(self.work_dir, self.KEY_FILE)
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        key = _Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return key

    def set_user_password(self, password: str):
        if not self._available:
            return
        salt_path = os.path.join(self.work_dir, self.SALT_FILE)
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                salt = f.read()
        else:
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
        kdf = _PBKDF2HMAC(
            algorithm=_hashes.SHA256(), length=32, salt=salt, iterations=200_000
        )
        derived = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        with open(os.path.join(self.work_dir, self.KEY_FILE), "wb") as f:
            f.write(derived)
        self._key = derived

    def encrypt_file(self, src_path: str, dst_path: str = None) -> str:
        if dst_path is None:
            dst_path = src_path + ".enc"
        if not self._available:
            # 降级：直接复制（不加密）
            with open(src_path, "rb") as fp:
                data = fp.read()
            with open(dst_path, "wb") as fp:
                fp.write(data)
            return dst_path
        f = _Fernet(self._key)
        with open(src_path, "rb") as fp:
            data = fp.read()
        token = f.encrypt(data)
        with open(dst_path, "wb") as fp:
            fp.write(token)
        return dst_path

    def decrypt_file(self, src_path: str, dst_path: str = None) -> str:
        if dst_path is None:
            dst_path = src_path[:-4] if src_path.endswith(".enc") else src_path + ".dec"
        if not self._available:
            with open(src_path, "rb") as fp:
                data = fp.read()
            with open(dst_path, "wb") as fp:
                fp.write(data)
            return dst_path
        f = _Fernet(self._key)
        with open(src_path, "rb") as fp:
            token = fp.read()
        data = f.decrypt(token)
        with open(dst_path, "wb") as fp:
            fp.write(data)
        return dst_path
