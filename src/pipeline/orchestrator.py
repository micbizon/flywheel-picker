import logging
import os
import time

from layer1_prescreener.main import run_prescreener_batch
from layer2_analysis.main import run_parallel_analysis
from layer3_selector.main import run_selector
from layer4_cases.main import run_cases
from layer5_portfolio_manager.batch import run_portfolio_manager_batch
from pipeline.checkpoint import (
    cleanup_old_checkpoints,
    get_completed_tickers,
    get_ticker_result,
    load_checkpoint,
    save_checkpoint,
    save_ticker_result,
    today_run_id,
)
from shared.config_loader import load_portfolio, load_watchlist
from shared.llm_client import reset_llm_clients
from shared.logging_config import close_decision_logger
from shared.market_data import get_pnl_pct

logger = logging.getLogger(__name__)


def _log(step: str, entered: int, exited: int) -> None:
    logger.info(f"{step}: wejście={entered}, wyjście={exited}")


def _call_with_retry(fn, *args, max_retries: int = None, **kwargs):
    if max_retries is None:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise
            is_connection = "Connection error" in str(e) or "ConnectError" in str(e)
            if is_connection:
                reset_llm_clients()
                logger.warning("Błąd sieci — klient zresetowany.")
            wait = 60 * attempt
            logger.warning(f"Próba {attempt + 1}/{max_retries} nieudana: {e} — retry za {wait}s")
            time.sleep(wait)


def run_pipeline(tickers: list[str] | None = None, run_l5: bool = False) -> None:
    cleanup_old_checkpoints()
    run_id = today_run_id()
    cp = load_checkpoint(run_id)
    if cp:
        logger.info(
            f"Wznawianie pipeline z checkpointu {run_id}: dostępne etapy: {list(cp.keys())}"
        )

    if tickers is None:
        watchlist = load_watchlist()
        tickers = (
            [t["ticker"] for t in watchlist.get("tickers", [])]
            if isinstance(watchlist.get("tickers"), list)
            else []
        )

    portfolio = load_portfolio()
    portfolio_tickers = {p["ticker"] for p in portfolio.get("positions", [])}

    all_tickers = list(dict.fromkeys(tickers + list(portfolio_tickers)))
    non_portfolio = [t for t in all_tickers if t not in portfolio_tickers]
    in_portfolio = [t for t in all_tickers if t in portfolio_tickers]

    logger.info(f"Ticki z portfolio (bypass prescreener): {in_portfolio}")
    logger.info(f"Ticki z watchlist (przez prescreener): {non_portfolio}")
    if overlap := [t for t in tickers if t in portfolio_tickers]:
        logger.info(f"Ticki w obu miejscach (watchlist + portfolio): {overlap}")

    logger.info(f"--- Warstwa 1: Pre-screener ({len(non_portfolio)} tickerów) ---")
    completed_l1 = get_completed_tickers(run_id, "l1")
    l1_results: dict[str, dict | None] = {}
    valid_completed_l1: set[str] = set()
    for t in completed_l1:
        result = get_ticker_result(run_id, "l1", t)
        if isinstance(result, dict) or result is None:
            l1_results[t] = result
            valid_completed_l1.add(t)
            logger.info(f"L1 {t}: wczytano z checkpointu")

    remaining_l1 = [t for t in non_portfolio if t not in valid_completed_l1]
    if remaining_l1:
        new_passing = _call_with_retry(run_prescreener_batch, remaining_l1)
        new_passing_map = {r["ticker"]: r for r in new_passing}
        for ticker in remaining_l1:
            result = new_passing_map.get(ticker)
            l1_results[ticker] = result
            save_ticker_result(run_id, "l1", ticker, result)

    passing = [r for r in l1_results.values() if r is not None]
    passing_tickers = [r["ticker"] for r in passing]
    _log("L1 prescreener", len(non_portfolio), len(passing_tickers))
    logger.info(f"  przeszły: {sorted(passing_tickers)}")
    if dropped_l1 := sorted(set(non_portfolio) - set(passing_tickers)):
        logger.info(f"  odpadły:  {dropped_l1}")

    layer2_tickers = list(dict.fromkeys(passing_tickers + in_portfolio))
    # layer2_tickers.remove("SQ")

    missing = [t for t in in_portfolio if t not in layer2_tickers]
    if missing:
        logger.error(f"BŁĄD: ticki z portfolio nie trafiły do warstwy 2: {missing}")

    logger.info(f"--- Warstwa 2: Analiza równoległa ({len(layer2_tickers)} tickerów) ---")
    completed_l2 = get_completed_tickers(run_id, "l2")
    layer2_tickers_set = set(layer2_tickers)
    layer2_results: dict[str, dict] = {
        t: get_ticker_result(run_id, "l2", t) for t in completed_l2 if t in layer2_tickers_set
    }
    for ticker in layer2_tickers:
        if ticker in completed_l2:
            logger.info(f"L2 {ticker}: wczytano z checkpointu")
            continue
        try:
            result = _call_with_retry(run_parallel_analysis, ticker)
            layer2_results[ticker] = result
            save_ticker_result(run_id, "l2", ticker, result)
        finally:
            close_decision_logger(ticker)
    _log("L2 analiza", len(layer2_tickers), len(layer2_results))
    logger.info(f"  wyjście: {sorted(layer2_results)}")

    logger.info("--- Warstwa 3: Selektor ---")
    selected = run_selector(list(layer2_results.values()))
    save_checkpoint(run_id, "l3", selected)
    _log("L3 selektor", len(layer2_results), len(selected))
    selected_tickers = sorted(e["ticker"] for e in selected)
    logger.info(f"  przeszły: {selected_tickers}")
    if dropped_l3 := sorted(set(layer2_results) - set(selected_tickers)):
        logger.info(f"  odpadły:  {dropped_l3}")

    logger.info(f"--- Warstwa 4: Bull/Bear/Pre-Mortem ({len(selected)} tickerów) ---")
    completed_l4 = get_completed_tickers(run_id, "l4")
    selected_tickers_set = {e["ticker"] for e in selected}
    layer4_results: dict[str, dict] = {
        t: get_ticker_result(run_id, "l4", t) for t in completed_l4 if t in selected_tickers_set
    }
    for entry in selected:
        ticker = entry["ticker"]
        if ticker in completed_l4:
            logger.info(f"L4 {ticker}: wczytano z checkpointu")
            continue
        try:
            result = _call_with_retry(run_cases, ticker, entry["analysis"])
            layer4_results[ticker] = result
            save_ticker_result(run_id, "l4", ticker, result)
        finally:
            close_decision_logger(ticker)
    _log("L4 cases", len(selected), len(layer4_results))
    logger.info(f"  wyjście: {sorted(layer4_results)}")

    missing_pm = [t for t in in_portfolio if t not in layer4_results]
    if missing_pm:
        logger.error(f"BŁĄD: ticki z portfolio nie trafiły do warstwy 4: {missing_pm}")

    pm_tickers = [e["ticker"] for e in selected]

    if not run_l5:
        logger.info("--- Warstwa 5: Portfolio Manager pominięta (użyj --portfolio-manager) ---")
        logger.info("--- Pipeline zakończony pomyślnie ---")
        return

    logger.info(f"--- Warstwa 5: Portfolio Manager ({len(pm_tickers)} tickerów) ---")
    portfolio_positions = {p["ticker"]: p for p in portfolio.get("positions", [])}
    candidates = []
    for ticker in pm_tickers:
        position = portfolio_positions.get(ticker)
        in_portfolio_flag = position is not None
        candidate = {
            "ticker": ticker,
            "in_portfolio": in_portfolio_flag,
            "current_size": position.get("current_weight_pct", 0) if position else 0,
            "pnl_pct": get_pnl_pct(ticker, position.get("entry_price", 0)) if position else None,
            "l2": layer2_results.get(ticker, {}),
            "l4": layer4_results.get(ticker, {}),
        }
        candidates.append(candidate)

    results = _call_with_retry(run_portfolio_manager_batch, candidates, portfolio)
    l5_results = {r["ticker"]: r for r in results}
    for ticker in pm_tickers:
        close_decision_logger(ticker)

    for ticker, result in l5_results.items():
        logger.info(
            f"  {ticker}: {result.get('action', '?')} "
            f"(current={result.get('current_position_size_pct', '?')}% "
            f"→ target={result.get('target_position_size_pct', '?')}%)"
        )
    _log("L5 portfolio manager", len(pm_tickers), len(l5_results))

    logger.info("--- Pipeline zakończony pomyślnie ---")
