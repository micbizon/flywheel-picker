import logging
from pathlib import Path

from shared.context import load_core_rules, read_template
from shared.llm_client import call_llm
from shared.logging_config import log_agent_result

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agents" / "01_prescreener.md"


def _format_company_info(ticker: str, metrics: dict) -> str:
    parts = [f"Ticker: {ticker}"]
    if metrics.get("long_name"):
        parts.append(f"Nazwa: {metrics['long_name']}")
    if metrics.get("sector") or metrics.get("industry"):
        parts.append(f"Sektor: {metrics.get('sector', '?')} / {metrics.get('industry', '?')}")
    rev = metrics.get("revenue_growth_yoy")
    gm = metrics.get("gross_margin")
    if rev is not None:
        parts.append(f"Wzrost przychodów YoY: {rev:.0%}")
    if gm is not None:
        parts.append(f"Gross margin: {gm:.0%}")
    return "\n".join(parts)


def _load_prompt(ticker: str, metrics: dict) -> str:
    company_info = _format_company_info(ticker, metrics)
    return (
        read_template(PROMPT_PATH)
        .replace("{{ CORE_RULES }}", load_core_rules())
        .replace("[TICKER]", ticker)
        .replace("[COMPANY_INFO]", company_info)
    )


def run_prescreener(ticker: str, metrics: dict | None = None) -> dict:
    prompt = _load_prompt(ticker, metrics or {})
    logger.debug(f"[prescreener] {ticker} prompt:\n{prompt}")
    result = call_llm(prompt)
    result["ticker"] = ticker
    log_agent_result(ticker, "prescreener", result)
    return result
