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
            api_key=cfg["api_key"],
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
        cfg["model_portfolio_manager"]
        if model_tier == "portfolio_manager"
        else cfg["model_analysis"]
    )
    client = _get_claude_client(cfg)
    kwargs = {
        "model": model,
        "max_tokens": 8192 if model_tier == "portfolio_manager" else 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if cfg["temperature"] is not None:
        kwargs["temperature"] = cfg["temperature"]
    with client.messages.stream(**kwargs) as stream:
        return stream.get_final_text()


def _call_openrouter(prompt: str, cfg: dict, model_tier: str = "analysis") -> str:
    model = (
        cfg["model_portfolio_manager"]
        if model_tier == "portfolio_manager"
        else cfg["model_analysis"]
    )
    chunks: list[str] = []
    with httpx.Client(
        timeout=httpx.Timeout(connect=30.0, read=600.0, write=600.0, pool=600.0)
    ) as client:
        with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 8192 if model_tier == "portfolio_manager" else 4096,
                **({"temperature": cfg["temperature"]} if cfg["temperature"] is not None else {}),
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                try:
                    data = json.loads(line[6:])
                    content = data["choices"][0]["delta"].get("content") or ""
                    if content:
                        chunks.append(content)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
    return "".join(chunks)


def _call_ollama(prompt: str, cfg: dict, model_tier: str = "analysis") -> str:
    model = (
        cfg["model_portfolio_manager"]
        if model_tier == "portfolio_manager"
        else cfg["model_analysis"]
    )
    response = httpx.post(
        f"{cfg['base_url']}/api/generate",
        json={"model": model, "prompt": prompt, "format": "json", "stream": False},
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
        except (json.JSONDecodeError, ValueError):
            pass

    logger.error(f"JSON parse failed: {response[:200]}")
    raise ValueError(f"Brak JSON w odpowiedzi: {response[:200]}")


def reset_llm_clients() -> None:
    global _claude_client
    _claude_client = None


def count_prompt_tokens(prompt: str, model_tier: str = "analysis") -> int:
    cfg = get_llm_config()
    if cfg["provider"] != "claude":
        return len(prompt) // 4
    model = (
        cfg["model_portfolio_manager"]
        if model_tier == "portfolio_manager"
        else cfg["model_analysis"]
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
    _callers = {
        "claude": _call_claude,
        "openrouter": _call_openrouter,
        "ollama": _call_ollama,
    }
    raw = _callers[cfg["provider"]](prompt, cfg, model_tier)
    logger.debug(f"Raw response:\n{raw}")
    if expect_json:
        return _safe_parse_json(raw)
    return raw
