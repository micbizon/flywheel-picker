import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _sort_watchlist(data: dict) -> dict:
    if "tickers" in data and isinstance(data["tickers"], list):
        data["tickers"] = sorted(
            data["tickers"], key=lambda t: t["ticker"] if isinstance(t, dict) else t
        )
    return data


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: str | Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )


def load_portfolio() -> dict:
    return load_yaml(DATA_DIR / "portfolio.yaml")


def load_watchlist() -> dict:
    path = DATA_DIR / "watchlist.yaml"
    if not path.exists():
        return {"tickers": []}
    data = load_yaml(path)
    if "tickers" not in data:
        data["tickers"] = []
    return _sort_watchlist(data)


def save_watchlist(data: dict) -> None:
    save_yaml(DATA_DIR / "watchlist.yaml", _sort_watchlist(data))


def _decisions_log_path() -> Path:
    mode = os.getenv("RUN_MODE", "test").lower()
    filename = (
        "decisions_log.yaml" if mode == "production" else "decisions_log_test.yaml"
    )
    return DATA_DIR / filename


def load_decisions_log() -> list:
    data = load_yaml(_decisions_log_path())
    return data.get("decisions", [])


def save_decisions_log(decisions: list) -> None:
    save_yaml(_decisions_log_path(), {"decisions": decisions})


def load_system_insights() -> dict:
    return load_yaml(DATA_DIR / "system_insights.yaml")


def save_system_insights(data: dict) -> None:
    save_yaml(DATA_DIR / "system_insights.yaml", data)


def get_llm_config() -> dict:
    use_claude = os.getenv("USE_CLAUDE_API", "false").lower() == "true"
    if use_claude:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("USE_CLAUDE_API=true ale brak ANTHROPIC_API_KEY w .env")
        return {
            "use_claude": True,
            "anthropic_api_key": api_key,
            "anthropic_temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.2")),
            "anthropic_model_analysis": os.getenv(
                "ANTHROPIC_MODEL_ANALYSIS", "claude-haiku-4-5-20251001"
            ),
            "anthropic_model_decision": os.getenv(
                "ANTHROPIC_MODEL_DECISION", "claude-sonnet-4-6"
            ),
        }
    return {
        "use_claude": use_claude,
        "ollama_model": os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


def get_active_model() -> str:
    cfg = get_llm_config()
    return "claude" if cfg["use_claude"] else cfg["ollama_model"]


def get_max_workers() -> int:
    return int(os.getenv("MAX_WORKERS", "4"))


def run_agents_parallel(agents: dict, *args) -> dict:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    with ThreadPoolExecutor(max_workers=get_max_workers()) as executor:
        futures = {executor.submit(fn, *args): name for name, fn in agents.items()}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results
