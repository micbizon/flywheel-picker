import json
from pathlib import Path

from shared.context import load_core_rules
from shared.llm_client import call_llm

PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "prompts" / "system" / "feedback_loop.md"
)


def run_feedback(decision: dict, current_data: dict, months: int) -> dict:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (
        template.replace("{{ CORE_RULES }}", load_core_rules())
        .replace("[DECISION]", json.dumps(decision, ensure_ascii=False, indent=2))
        .replace(
            "[CURRENT_DATA]", json.dumps(current_data, ensure_ascii=False, indent=2)
        )
        .replace("[MONTHS]", str(months))
    )
    return call_llm(prompt, model_tier="decision")
