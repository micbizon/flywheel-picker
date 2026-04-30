import logging
from pathlib import Path

from shared.context import load_core_rules, read_template
from shared.llm_client import call_llm
from shared.logging_config import log_agent_result

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "agents"


def _load_prompt(
    filename: str,
    ticker: str,
    price_context: str = "",
    company_name_context: str = "",
) -> str:
    return (
        read_template(PROMPTS_DIR / filename)
        .replace("{{ CORE_RULES }}", load_core_rules())
        .replace("[TICKER]", ticker)
        .replace("{{ PRICE_CONTEXT }}", price_context)
        .replace("{{ COMPANY_NAME_CONTEXT }}", company_name_context)
    )


def run_fundamental(ticker: str, name_ctx: str) -> dict:
    result = call_llm(_load_prompt("02a_fundamental.md", ticker, company_name_context=name_ctx))
    result["ticker"] = ticker
    log_agent_result(ticker, "fundamental", result)
    return result


def run_technical(ticker: str, name_ctx: str, price_ctx: str) -> dict:
    result = call_llm(
        _load_prompt("02b_technical.md", ticker, price_ctx, company_name_context=name_ctx)
    )
    result["ticker"] = ticker
    log_agent_result(ticker, "technical", result)
    return result


def run_sentiment(ticker: str, sentiment_ctx: str) -> dict:
    result = call_llm(_load_prompt("02c_sentiment.md", ticker, company_name_context=sentiment_ctx))
    result["ticker"] = ticker
    log_agent_result(ticker, "sentiment", result)
    return result


def run_ownership(ticker: str, ownership_ctx: str) -> dict:
    result = call_llm(_load_prompt("02d_ownership.md", ticker, company_name_context=ownership_ctx))
    result["ticker"] = ticker
    log_agent_result(ticker, "ownership", result)
    return result
