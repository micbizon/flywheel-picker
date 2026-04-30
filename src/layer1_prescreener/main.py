import logging

from shared.logging_config import close_decision_logger

from .agent import run_prescreener
from .prefilter import apply_prefilter

logger = logging.getLogger(__name__)

PASSING_VERDICTS = {"PASS", "CONDITIONAL_PASS"}


def run_prescreener_batch(tickers: list[str]) -> list[dict]:
    passing, _ = apply_prefilter(tickers)
    results = []
    for entry in passing:
        ticker = entry["ticker"]
        metrics = entry["metrics"]
        try:
            result = run_prescreener(ticker, metrics)
            verdict = result.get("verdict", "UNKNOWN")
            logger.info(f"[prescreener] {ticker}: {verdict}")
            if verdict in PASSING_VERDICTS:
                results.append(result)
        except Exception as e:
            logger.warning(f"[prescreener] {ticker}: błąd parsowania — traktuję jako REJECT ({e})")
        finally:
            close_decision_logger(ticker)
    passed = len(results)
    logger.info(f"[prescreener] {passed}/{len(tickers)} tickerów przeszło filtr")
    return results
