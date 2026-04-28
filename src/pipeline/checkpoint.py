import json
import logging
import time
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "logs" / "checkpoints"


def checkpoint_path(run_id: str) -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR / f"{run_id}.json"


def save_checkpoint(run_id: str, stage: str, data) -> None:
    path = checkpoint_path(run_id)
    checkpoint = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    checkpoint[stage] = data
    path.write_text(json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8")


def load_checkpoint(run_id: str) -> dict:
    path = checkpoint_path(run_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def clear_checkpoint(run_id: str) -> None:
    path = checkpoint_path(run_id)
    if path.exists():
        path.unlink()


def save_ticker_result(run_id: str, stage: str, ticker: str, data: dict) -> None:
    path = checkpoint_path(run_id)
    checkpoint = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if stage not in checkpoint:
        checkpoint[stage] = {}
    checkpoint[stage][ticker] = data
    path.write_text(json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8")


def get_ticker_result(run_id: str, stage: str, ticker: str) -> dict | None:
    return load_checkpoint(run_id).get(stage, {}).get(ticker)


def get_completed_tickers(run_id: str, stage: str) -> set[str]:
    return set(load_checkpoint(run_id).get(stage, {}).keys())


def cleanup_old_checkpoints(max_age_days: int = 2) -> None:
    if not CHECKPOINT_DIR.exists():
        return
    cutoff = time.time() - (max_age_days * 24 * 3600)
    for f in CHECKPOINT_DIR.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            logger.debug(f"Usunięto stary checkpoint: {f.name}")


def today_run_id() -> str:
    return date.today().isoformat()
