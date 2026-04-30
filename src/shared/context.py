from datetime import date
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=None)
def read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_core_rules() -> str:
    return (
        read_template(PROMPTS_DIR / "CORE_RULES.md")
        + "\n"
        + read_template(PROMPTS_DIR / "RESPONSE_RULES.md")
    ).replace("{{ CURRENT_DATE }}", date.today().isoformat())
