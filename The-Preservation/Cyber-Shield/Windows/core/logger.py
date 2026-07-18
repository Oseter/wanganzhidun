"""日志模块：分级日志，同时写文件与系统托盘气泡。"""
import logging
import os
import sys
from datetime import datetime


def _default_log_dir() -> str:
    """安装/打包后日志写程序目录，开发期写当前目录。"""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "logs")
    return "logs"


def setup_logger(log_dir: str = None, level: int = logging.INFO) -> logging.Logger:
    """初始化日志器，输出到 logs/app_YYYYMMDD.log。"""
    log_dir = log_dir or _default_log_dir()
    os.makedirs(log_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(log_dir, f"app_{date_str}.log")

    logger = logging.getLogger("WangAnZhiDun")
    logger.setLevel(level)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 控制台 handler（调试用，打包后无窗口也不影响）
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


# 全局默认实例
log = setup_logger()
