"""日志模块：分级日志，同时写文件与系统托盘气泡。"""
import logging
import os
from datetime import datetime


def setup_logger(log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """初始化日志器，输出到 logs/app_YYYYMMDD.log。"""
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
