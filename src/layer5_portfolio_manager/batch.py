import json
import logging
from pathlib import Path

from shared.context import read_template
from shared.llm_client import call_llm, count_prompt_tokens
from shared.logger import save_decision
from shared.logging_config import get_decision_logger

from .context_builder_batch import build_allocator_context, build_batch_context

logger = logging.getLogger(__name__)

_MAX_INPUT_TOKENS = 200_000
_WARN_AT = 0.95

_SCREENER_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "agents" / "05a_portfolio_screener.md"
)
_ALLOCATOR_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "agents" / "05b_portfolio_allocator.md"
)


def _log_token_count(label: str, prompt: str) -> None:
    count = count_prompt_tokens(prompt, model_tier="portfolio_manager")
    pct = count / _MAX_INPUT_TOKENS * 100
    logger.info(f"PM {label}: {count} tokenów ({pct:.1f}% limitu)")
    if count > _MAX_INPUT_TOKENS * _WARN_AT:
        logger.warning(f"PM {label} bliski limitu: {count}/{_MAX_INPUT_TOKENS} tokenów")


def run_portfolio_manager_batch(
    candidates: list[dict],
    portfolio: dict,
) -> list[dict]:
    candidates = sorted(candidates, key=lambda c: 0 if c["in_portfolio"] else 1)
    n = len(candidates)

    # Faza 1 — ewaluacja wszystkich kandydatów
    context_p1 = build_batch_context(candidates, portfolio)
    prompt_p1 = (
        read_template(_SCREENER_PROMPT_PATH)
        .replace("{{ FULL_CONTEXT }}", context_p1)
        .replace("[N]", str(n))
    )
    _log_token_count("faza 1", prompt_p1)
    phase1_raw = call_llm(prompt_p1, model_tier="portfolio_manager")
    phase1_results: list[dict] = phase1_raw if isinstance(phase1_raw, list) else [phase1_raw]
    logger.info(f"PM faza 1: {len(phase1_results)}/{n} tickerów ocenionych")

    by_ticker = {c["ticker"]: c for c in candidates}
    buy_candidates = [
        r
        for r in phase1_results
        if not by_ticker.get(r["ticker"], {}).get("in_portfolio")
        and r.get("verdict") == "BUY_CANDIDATE"
    ]
    portfolio_entries = [
        r for r in phase1_results if by_ticker.get(r["ticker"], {}).get("in_portfolio")
    ]
    phase2_input = portfolio_entries + buy_candidates
    logger.info(
        f"PM faza 2: {len(portfolio_entries)} portfolio + {len(buy_candidates)} BUY kandydatów"
    )

    # Faza 2 — alokacja
    context_p2 = build_allocator_context(phase2_input, candidates, portfolio)
    prompt_p2 = read_template(_ALLOCATOR_PROMPT_PATH).replace("{{ FULL_CONTEXT }}", context_p2)
    _log_token_count("faza 2", prompt_p2)
    phase2_raw = call_llm(prompt_p2, model_tier="portfolio_manager")
    phase2_results: list[dict] = phase2_raw if isinstance(phase2_raw, list) else [phase2_raw]

    # Merge: faza 2 dla actionable tickerów, PASS z fazy 1 dla reszty
    phase2_by_ticker = {r["ticker"]: r for r in phase2_results}
    final: list[dict] = []
    for r in phase1_results:
        ticker = r["ticker"]
        if ticker in phase2_by_ticker:
            final.append(phase2_by_ticker[ticker])
        else:
            final.append(
                {
                    "ticker": ticker,
                    "action": "PASS",
                    "current_position_size_pct": 0,
                    "target_position_size_pct": 0,
                    "entry_price": 0.0,
                    "rationale": r.get("note", ""),
                }
            )

    for result in final:
        ticker = result.get("ticker", "?")
        action = result.get("action", "")
        dec_log = get_decision_logger(ticker)
        dec_log.info(
            f"[portfolio_manager_batch] action={action} "
            f"current={result.get('current_position_size_pct', 0)}% "
            f"target={result.get('target_position_size_pct', 0)}%"
        )
        dec_log.info(f"[portfolio_manager_batch] rationale: {result.get('rationale', '')}")
        dec_log.debug(f"[portfolio_manager_batch] full: {json.dumps(result, ensure_ascii=False)}")
        if action not in (None, "", "PASS"):
            save_decision(result)

    return final
