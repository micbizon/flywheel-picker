import logging
from datetime import date

from layer0_ideas.insider_buying import fetch_insider_buys
from layer0_ideas.screener import fetch_screener_candidates
from shared.config_loader import load_watchlist, save_watchlist

logger = logging.getLogger(__name__)


def run_idea_generation() -> None:
    watchlist = load_watchlist()
    existing = {entry["ticker"] for entry in watchlist["tickers"] if isinstance(entry, dict)}

    insider_tickers = fetch_insider_buys()
    if not insider_tickers:
        logger.info("idea_generation: insider_buying niedostępny — używam tylko screener")
    screener_tickers = fetch_screener_candidates()

    today = date.today().isoformat()
    added = 0

    for ticker in insider_tickers:
        if ticker not in existing:
            watchlist["tickers"].append(
                {"ticker": ticker, "source": "insider_buying", "discovery_date": today}
            )
            existing.add(ticker)
            added += 1

    for ticker in screener_tickers:
        if ticker not in existing:
            watchlist["tickers"].append(
                {"ticker": ticker, "source": "screener", "discovery_date": today}
            )
            existing.add(ticker)
            added += 1

    save_watchlist(watchlist)
    logger.info(f"idea_generation: added {added} new tickers to watchlist")
