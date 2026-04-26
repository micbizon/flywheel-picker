import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from layer1_prescreener.main import run_prescreener_batch
from layer2_analysis.main import run_parallel_analysis
from layer3_selector.main import run_selector
from layer4_cases.main import run_cases
from layer5_portfolio_manager.main import run_portfolio_manager
from shared.config_loader import get_max_workers, load_portfolio, load_watchlist

logger = logging.getLogger(__name__)

_TOP_N_FOR_PM = 5


def _log(step: str, entered: int, exited: int) -> None:
    logger.info(f"{step}: wejście={entered}, wyjście={exited}")


def _call_with_retry(fn, *args, max_retries: int = None, **kwargs):
    if max_retries is None:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                logger.warning(f"Próba {attempt}/{max_retries} nieudana: {e}")
                raise
            wait = 2 ** (attempt - 1)
            logger.warning(
                f"Próba {attempt}/{max_retries} nieudana: {e} — retry za {wait}s"
            )
            time.sleep(wait)


def run_pipeline(tickers: list[str] | None = None) -> None:
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
    passing = run_prescreener_batch(non_portfolio)
    passing_tickers = [r["ticker"] for r in passing]
    _log("L1 prescreener", len(non_portfolio), len(passing_tickers))

    layer2_tickers = list(dict.fromkeys(passing_tickers + in_portfolio))

    missing = [t for t in in_portfolio if t not in layer2_tickers]
    if missing:
        logger.error(f"BŁĄD: ticki z portfolio nie trafiły do warstwy 2: {missing}")

    logger.info(
        f"--- Warstwa 2: Analiza równoległa ({len(layer2_tickers)} tickerów) ---"
    )

    layer2_results: dict[str, dict] = {}
    with ThreadPoolExecutor(
        max_workers=min(len(layer2_tickers), get_max_workers())
    ) as ex:
        futures = {
            ex.submit(_call_with_retry, run_parallel_analysis, t): t
            for t in layer2_tickers
        }
        for future in as_completed(futures):
            ticker = futures[future]
            layer2_results[ticker] = future.result()
    _log("L2 analiza", len(layer2_tickers), len(layer2_results))

    logger.info("--- Warstwa 3: Selektor ---")
    analyses = list(layer2_results.values())
    selected = run_selector(analyses)
    _log("L3 selektor", len(analyses), len(selected))

    logger.info(f"--- Warstwa 4: Bull/Bear/Pre-Mortem ({len(selected)} tickerów) ---")
    layer4_results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(len(selected), get_max_workers())) as ex:
        futures = {
            ex.submit(
                _call_with_retry, run_cases, entry["ticker"], entry["analysis"]
            ): entry["ticker"]
            for entry in selected
        }
        for future in as_completed(futures):
            ticker = futures[future]
            layer4_results[ticker] = future.result()
    _log("L4 cases", len(selected), len(layer4_results))

    missing_pm = [t for t in in_portfolio if t not in layer4_results]
    if missing_pm:
        logger.error(f"BŁĄD: ticki z portfolio nie trafiły do warstwy 4: {missing_pm}")

    top5_tickers = [e["ticker"] for e in selected if not e["in_portfolio"]][
        :_TOP_N_FOR_PM
    ]
    pm_tickers = list(dict.fromkeys(top5_tickers + in_portfolio))

    logger.info(f"--- Warstwa 5: Portfolio Manager ({len(pm_tickers)} tickerów) ---")
    for ticker in pm_tickers:
        l2 = layer2_results.get(ticker, {})
        l4 = layer4_results.get(ticker, {})
        try:
            result = _call_with_retry(run_portfolio_manager, ticker, l2, l4)
            logger.info(
                f"  {ticker}: {result.get('action', '?')} "
                f"(current={result.get('current_position_size_pct', '?')}% "
                f"→ target={result.get('target_position_size_pct', '?')}%)"
            )
        except ValueError as e:
            logger.error(f"  {ticker}: BŁĄD parsowania JSON — pomijam ({e})")
            continue
        except Exception as e:
            logger.error(f"  {ticker}: NIEOCZEKIWANY BŁĄD — pomijam ({e})")
            continue
    _log("L5 portfolio manager", len(pm_tickers), len(pm_tickers))

    logger.info("--- Pipeline zakończony ---")
