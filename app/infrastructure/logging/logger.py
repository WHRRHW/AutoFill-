from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os


def _default_log_dir() -> Path:
    # %APPDATA%/AutoFill/logs
    appdata = os.getenv("APPDATA") or str(Path.home())
    return Path(appdata) / "AutoFill" / "logs"


def get_logger(name: str = "autofill") -> logging.Logger:
    """
    本地日志（对齐 TRD）：
    - 仅记录流程节点与错误信息
    - 不记录源文档全文
    - 不记录任何 API key
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    # TRD：INFO 流程节点 / WARNING 重试与字段告警 / ERROR 失败
    logger.setLevel(logging.DEBUG)
    log_dir = _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=str(log_dir / "autofill.log"),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger

