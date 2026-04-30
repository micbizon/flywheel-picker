from functools import partial

from shared.config_loader import run_agents_parallel
from shared.market_data import get_price_context

from .agents import run_bear, run_bull, run_premortem


def run_cases(ticker: str, layer2_context: dict) -> dict:
    price_ctx = get_price_context(ticker)
    agents = {
        "bull": partial(run_bull, price_ctx=price_ctx),
        "bear": partial(run_bear, price_ctx=price_ctx),
        "premortem": run_premortem,
    }
    return run_agents_parallel(agents, ticker, layer2_context)
