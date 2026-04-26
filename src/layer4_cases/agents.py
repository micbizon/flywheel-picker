import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from shared.config_loader import get_max_workers
from shared.context import load_core_rules, read_template
from shared.llm_client import call_llm
from shared.logging_config import log_agent_result
from shared.market_data import get_price_context

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "agents"


def _get_instances() -> int:
    return int(os.getenv("AGENT_INSTANCES", "3"))


def _load_prompt(
    filename: str,
    ticker: str,
    layer2_context: dict,
    extra: dict = None,
    price_context: str = "",
) -> str:
    prompt = (
        read_template(PROMPTS_DIR / filename)
        .replace("{{ CORE_RULES }}", load_core_rules())
        .replace("[TICKER]", ticker)
        .replace(
            "[LAYER2_CONTEXT]", json.dumps(layer2_context, ensure_ascii=False, indent=2)
        )
        .replace("{{ PRICE_CONTEXT }}", price_context)
    )
    if extra:
        for key, value in extra.items():
            prompt = prompt.replace(key, str(value))
    return prompt


def _load_synthesizer_prompt(
    filename: str, ticker: str, analyses_json: str, n: int
) -> str:
    return (
        read_template(PROMPTS_DIR / filename)
        .replace("{{ CORE_RULES }}", load_core_rules())
        .replace("[TICKER]", ticker)
        .replace("[N]", str(n))
        .replace("[BULL_ANALYSES]", analyses_json)
        .replace("[BEAR_ANALYSES]", analyses_json)
        .replace("[PREMORTEM_ANALYSES]", analyses_json)
    )


def _run_bull_single(ticker: str, layer2_context: dict) -> dict:
    price_ctx = get_price_context(ticker)
    result = call_llm(
        _load_prompt("04a_bull.md", ticker, layer2_context, price_context=price_ctx)
    )
    result["ticker"] = ticker
    log_agent_result(ticker, "bull_instance", result)
    return result


def _run_bear_single(ticker: str, layer2_context: dict) -> dict:
    price_ctx = get_price_context(ticker)
    result = call_llm(
        _load_prompt("04b_bear.md", ticker, layer2_context, price_context=price_ctx)
    )
    result["ticker"] = ticker
    log_agent_result(ticker, "bear_instance", result)
    return result


def _run_premortem_single(ticker: str, layer2_context: dict) -> dict:
    future_year = datetime.now().year + 2
    prompt = _load_prompt(
        "04c_premortem.md", ticker, layer2_context, {"[FUTURE_YEAR]": future_year}
    )
    result = call_llm(prompt)
    result["ticker"] = ticker
    log_agent_result(ticker, "premortem_instance", result)
    return result


def _run_bull_synthesizer(ticker: str, analyses: list[dict]) -> dict:
    n = len(analyses)
    analyses_json = json.dumps(analyses, ensure_ascii=False, indent=2)
    prompt = _load_synthesizer_prompt(
        "04a_bull_synthesizer.md", ticker, analyses_json, n
    )
    result = call_llm(prompt, model_tier="decision")
    result["ticker"] = ticker
    log_agent_result(ticker, "bull_synthesizer", result)
    return result


def _run_bear_synthesizer(ticker: str, analyses: list[dict]) -> dict:
    n = len(analyses)
    analyses_json = json.dumps(analyses, ensure_ascii=False, indent=2)
    prompt = _load_synthesizer_prompt(
        "04b_bear_synthesizer.md", ticker, analyses_json, n
    )
    result = call_llm(prompt, model_tier="decision")
    result["ticker"] = ticker
    log_agent_result(ticker, "bear_synthesizer", result)
    return result


def _run_premortem_synthesizer(ticker: str, analyses: list[dict]) -> dict:
    n = len(analyses)
    analyses_json = json.dumps(analyses, ensure_ascii=False, indent=2)
    prompt = _load_synthesizer_prompt(
        "04c_premortem_synthesizer.md", ticker, analyses_json, n
    )
    result = call_llm(prompt, model_tier="decision")
    result["ticker"] = ticker
    log_agent_result(ticker, "premortem_synthesizer", result)
    return result


def run_bull(ticker: str, layer2_context: dict) -> dict:
    n = _get_instances()
    with ThreadPoolExecutor(max_workers=min(n, get_max_workers())) as ex:
        futures = [
            ex.submit(_run_bull_single, ticker, layer2_context) for _ in range(n)
        ]
        analyses = [f.result() for f in as_completed(futures)]
    return _run_bull_synthesizer(ticker, analyses)


def run_bear(ticker: str, layer2_context: dict) -> dict:
    n = _get_instances()
    with ThreadPoolExecutor(max_workers=min(n, get_max_workers())) as ex:
        futures = [
            ex.submit(_run_bear_single, ticker, layer2_context) for _ in range(n)
        ]
        analyses = [f.result() for f in as_completed(futures)]
    return _run_bear_synthesizer(ticker, analyses)


def run_premortem(ticker: str, layer2_context: dict) -> dict:
    n = _get_instances()
    with ThreadPoolExecutor(max_workers=min(n, get_max_workers())) as ex:
        futures = [
            ex.submit(_run_premortem_single, ticker, layer2_context) for _ in range(n)
        ]
        analyses = [f.result() for f in as_completed(futures)]
    return _run_premortem_synthesizer(ticker, analyses)
