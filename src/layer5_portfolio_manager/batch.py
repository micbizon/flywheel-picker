import json
import logging
from pathlib import Path

from shared.context import read_template
from shared.llm_client import call_llm, count_prompt_tokens
from shared.logger import save_decision
from shared.logging_config import get_decision_logger

from .context_builder_batch import build_batch_context

logger = logging.getLogger(__name__)

_MAX_INPUT_TOKENS = 200_000
_WARN_AT = 0.95

PROMPT_PATH = (
    Path(__file__).parent.parent.parent
    / "prompts"
    / "agents"
    / "05_portfolio_manager.md"
)


def run_portfolio_manager_batch(
    candidates: list[dict],
    portfolio: dict,
) -> list[dict]:
    context = build_batch_context(candidates, portfolio)
    prompt = read_template(PROMPT_PATH).replace("{{ FULL_CONTEXT }}", context)
    token_count = count_prompt_tokens(prompt, model_tier="portfolio_manager")
    token_pct = token_count / _MAX_INPUT_TOKENS * 100
    logger.info(f"PM prompt: {token_count} tokenów ({token_pct:.1f}% limitu)")
    if token_count > _MAX_INPUT_TOKENS * _WARN_AT:
        logger.warning(
            f"PM prompt bliski limitu: {token_count}/{_MAX_INPUT_TOKENS} tokenów ({token_pct:.1f}%)"
        )

    raw = call_llm(prompt, model_tier="portfolio_manager")
    logger.debug(
        f"PM raw type: {type(raw)}, len: {len(raw) if isinstance(raw, list) else 'N/A'}"
    )
    if isinstance(raw, list):
        logger.debug(f"PM tickers received: {[r.get('ticker') for r in raw]}")

    results: list[dict] = raw if isinstance(raw, list) else [raw]

    for result in results:
        ticker = result.get("ticker", "?")
        action = result.get("action", "")
        dec_log = get_decision_logger(ticker)
        dec_log.info(
            f"[portfolio_manager_batch] action={action} "
            f"current={result.get('current_position_size_pct', 0)}% "
            f"target={result.get('target_position_size_pct', 0)}%"
        )
        dec_log.info(
            f"[portfolio_manager_batch] rationale: {result.get('rationale', '')}"
        )
        dec_log.debug(
            f"[portfolio_manager_batch] full: {json.dumps(result, ensure_ascii=False)}"
        )
        if action not in (None, "", "PASS"):
            save_decision(result)

    return results
