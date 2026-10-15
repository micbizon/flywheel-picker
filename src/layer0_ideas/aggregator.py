import logging

from layer0_ideas.insider_buying import fetch_insider_buys
from layer0_ideas.screener import fetch_screener_candidates
from shared.config_loader import load_watchlist, save_watchlist

logger = logging.getLogger(__name__)


def run_idea_generation() -> None:
    existing = set(load_watchlist())

    insider_tickers = fetch_insider_buys()
    if not insider_tickers:
        logger.info("idea_generation: insider_buying niedostępny — używam tylko screener")
    screener_tickers = fetch_screener_candidates()

    new_tickers = [t for t in insider_tickers + screener_tickers if t not in existing]
    save_watchlist(sorted(existing | set(new_tickers)))
    logger.info(f"idea_generation: added {len(new_tickers)} new tickers to watchlist")
