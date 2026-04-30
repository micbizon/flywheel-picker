from functools import partial

from shared.config_loader import run_agents_parallel
from shared.market_data import (
    get_company_name_context,
    get_ownership_context,
    get_price_context,
    get_sentiment_context,
)

from .agents import run_fundamental, run_ownership, run_sentiment, run_technical


def run_parallel_analysis(ticker: str) -> dict:
    name_ctx = get_company_name_context(ticker)
    price_ctx = get_price_context(ticker)
    sentiment_ctx = get_sentiment_context(ticker)
    ownership_ctx = get_ownership_context(ticker)

    agents = {
        "fundamental": partial(run_fundamental, name_ctx=name_ctx),
        "technical": partial(run_technical, name_ctx=name_ctx, price_ctx=price_ctx),
        "sentiment": partial(run_sentiment, sentiment_ctx=sentiment_ctx),
        "ownership": partial(run_ownership, ownership_ctx=ownership_ctx),
    }
    return run_agents_parallel(agents, ticker)
