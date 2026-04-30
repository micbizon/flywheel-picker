import logging
import os
import threading
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
_LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
_logger_lock = threading.Lock()
_DECISIONS_DIR = _LOGS_DIR / "decisions"
_DECISIONS_MAX_AGE_DAYS = 90


def _cleanup_old_decisions() -> None:
    cutoff = time.time() - (_DECISIONS_MAX_AGE_DAYS * 24 * 3600)
    for f in _DECISIONS_DIR.glob("*.log"):
        if f.stat().st_mtime < cutoff:
            f.unlink()


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    _LOGS_DIR.mkdir(exist_ok=True)
    _DECISIONS_DIR.mkdir(exist_ok=True)

    _cleanup_old_decisions()

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = TimedRotatingFileHandler(
        _LOGS_DIR / "pipeline.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)


def get_decision_logger(ticker: str) -> logging.Logger:
    from datetime import date

    name = f"decisions.{date.today().isoformat()}_{ticker}"
    with _logger_lock:
        log = logging.getLogger(name)
        if not log.handlers:
            log.setLevel(logging.DEBUG)
            log.propagate = False
            _DECISIONS_DIR.mkdir(exist_ok=True)
            filename = _DECISIONS_DIR / f"{date.today().isoformat()}_{ticker}.log"
            handler = logging.FileHandler(filename, encoding="utf-8")
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter(_LOG_FORMAT))
            log.addHandler(handler)
        return log


def log_agent_result(ticker: str, agent_name: str, result: dict) -> None:
    dec_log = get_decision_logger(ticker)
    fields = {k: result[k] for k in ("verdict",) if result.get(k) is not None}
    summary = " ".join(f"{k}={v}" for k, v in fields.items()) or "ok"
    dec_log.info(f"[{agent_name}] {summary}")
    dec_log.debug(f"[{agent_name}] raw_analysis: {result.get('raw_analysis', '')}")


def close_decision_logger(ticker: str) -> None:
    from datetime import date

    name = f"decisions.{date.today().isoformat()}_{ticker}"
    log = logging.getLogger(name)
    for handler in log.handlers[:]:
        handler.close()
        log.removeHandler(handler)
