import os

AGENT_WEIGHTS = {
    "fundamental": 0.35,
    "ownership": 0.30,
    "sentiment": 0.20,
    "technical": 0.15,
}
VERDICT_SCORES = {"PASS": 2, "WATCH": 1, "REJECT": 0}
TOP_N = int(os.getenv("TOP_N", "20"))
MIN_SCORE_THRESHOLD = 1.0
