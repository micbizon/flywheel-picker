import json
import logging

import anthropic
import httpx
from json_repair import repair_json

from shared.config_loader import get_llm_config

logger = logging.getLogger(__name__)

_claude_client: anthropic.Anthropic | None = None


def _get_claude_client(cfg: dict) -> anthropic.Anthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = anthropic.Anthropic(
            api_key=cfg["anthropic_api_key"],
            timeout=httpx.Timeout(
                connect=30.0,
                read=600.0,
                write=600.0,
                pool=600.0,
            ),
        )
    return _claude_client


def _call_claude(prompt: str, cfg: dict, model_tier: str = "analysis") -> str:
    model = (
        cfg["anthropic_model_portfolio_manager"]
        if model_tier == "portfolio_manager"
        else cfg["anthropic_model_analysis"]
    )
    client = _get_claude_client(cfg)
    with client.messages.stream(
        model=model,
        max_tokens=8192 if model_tier == "portfolio_manager" else 4096,
        temperature=cfg.get("anthropic_temperature", 0.2),
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        return stream.get_final_text()


def _call_ollama(prompt: str, cfg: dict) -> str:
    response = httpx.post(
        f"{cfg['ollama_base_url']}/api/generate",
        json={"model": cfg["ollama_model"], "prompt": prompt, "stream": False},
        timeout=1800.0,
    )
    response.raise_for_status()
    return response.json()["response"]


def _safe_parse_json(response: str) -> dict | list:
    if not response or not response.strip():
        raise ValueError("Model zwrócił pustą odpowiedź")
    response = response.strip()

    try:
        result = json.loads(response)
        if isinstance(result, (dict, list)):
            return result
    except json.JSONDecodeError:
        pass

    # Determine structure type by first JSON character in response
    first_json_char = next((ch for ch in response if ch in ("{", "[")), None)
    if first_json_char == "[":
        start = response.find("[")
        end = response.rfind("]")
    else:
        start = response.find("{")
        end = response.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(response[start : end + 1])
            if isinstance(result, (dict, list)):
                return result
        except json.JSONDecodeError:
            pass

    if start != -1:
        try:
            result = json.loads(repair_json(response[start:]))
            if isinstance(result, (dict, list)):
                return result
        except json.JSONDecodeError, ValueError:
            pass

    logger.error(f"JSON parse failed: {response[:200]}")
    raise ValueError(f"Brak JSON w odpowiedzi: {response[:200]}")


def reset_claude_client() -> None:
    global _claude_client
    _claude_client = None


def count_prompt_tokens(prompt: str, model_tier: str = "analysis") -> int:
    cfg = get_llm_config()
    if not cfg["use_claude"]:
        return len(prompt) // 4
    model = (
        cfg["anthropic_model_portfolio_manager"]
        if model_tier == "portfolio_manager"
        else cfg["anthropic_model_analysis"]
    )
    client = _get_claude_client(cfg)
    response = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.input_tokens


def call_llm(
    prompt: str, expect_json: bool = True, model_tier: str = "analysis"
) -> str | dict | list:
    cfg = get_llm_config()
    logger.debug(f"Prompt:\n{prompt}")
    raw = (
        _call_claude(prompt, cfg, model_tier)
        if cfg["use_claude"]
        else _call_ollama(prompt, cfg)
    )
    logger.debug(f"Raw response:\n{raw}")
    if expect_json:
        return _safe_parse_json(raw)
    return raw
