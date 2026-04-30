import logging
from datetime import date
from pathlib import Path

from shared.llm_client import call_llm
from shared.logger import save_decision
from shared.logging_config import get_decision_logger

from .context_builder import build_context

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "agents" / "05_portfolio_manager.md"


def _build_decision_payload(ticker: str, pm_result: dict) -> dict:
    return {
        "ticker": ticker,
        "action": pm_result.get("action", ""),
        "current_position_size_pct": pm_result.get("current_position_size_pct", 0),
        "target_position_size_pct": pm_result.get("target_position_size_pct", 0),
        "entry_price": pm_result.get("entry_price", 0.0),
        "entry_price_currency": "USD",
        "rationale": pm_result.get("rationale", ""),
        "stop_loss_price": pm_result.get("stop_loss_price", 0.0),
        "stop_loss_fundamental": pm_result.get("stop_loss_fundamental", ""),
        "checkin_1yr_criteria": pm_result.get("checkin_1yr_criteria", ""),
        "feedback_6m": None,
        "feedback_12m": None,
    }


def run_portfolio_manager(ticker: str, layer2: dict, layer4: dict) -> dict:
    context = build_context(ticker, layer2, layer4)
    logger.debug(f"CONTEXT PREVIEW:\n{context}")
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.replace("{{ FULL_CONTEXT }}", context)

    pm_result = call_llm(prompt, model_tier="decision")
    pm_result["ticker"] = ticker

    dec_log = get_decision_logger(ticker)
    dec_log.info(
        f"[portfolio_manager] action={pm_result.get('action')} "
        f"current={pm_result.get('current_position_size_pct', 0)}% "
        f"target={pm_result.get('target_position_size_pct', 0)}%"
    )
    dec_log.info(f"[portfolio_manager] rationale: {pm_result.get('rationale', '')}")

    if pm_result.get("action") == "PASS":
        dec_log.info("[portfolio_manager] action=PASS — nie zapisuję do decisions_log")
        return pm_result

    payload = _build_decision_payload(ticker, pm_result)
    payload["date"] = str(date.today())
    save_decision(payload)

    return pm_result
