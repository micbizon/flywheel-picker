import logging

from shared.config_loader import load_portfolio

from .weights import AGENT_WEIGHTS, MIN_SCORE_THRESHOLD, TOP_N, VERDICT_SCORES

logger = logging.getLogger(__name__)


def _weighted_score(analysis: dict) -> float:
    total = 0.0
    for agent, weight in AGENT_WEIGHTS.items():
        verdict = analysis.get(agent, {}).get("verdict", "REJECT")
        total += VERDICT_SCORES.get(verdict, 0) * weight
    return round(total, 4)


def run_selector(analyses: list[dict]) -> list[dict]:
    portfolio = load_portfolio()
    portfolio_tickers = {p["ticker"] for p in portfolio.get("positions", [])}

    scored = []
    for analysis in analyses:
        ticker = next(
            (v.get("ticker") for v in analysis.values() if isinstance(v, dict) and v.get("ticker")),
            None,
        )
        if ticker is None:
            continue
        entry = {
            "ticker": ticker,
            "weighted_score": _weighted_score(analysis),
            "in_portfolio": ticker in portfolio_tickers,
            "analysis": analysis,
        }
        scored.append(entry)

    scored.sort(key=lambda x: x["weighted_score"], reverse=True)

    portfolio_entries = [e for e in scored if e["in_portfolio"]]
    non_portfolio = [e for e in scored if not e["in_portfolio"]]

    top = non_portfolio[:TOP_N - len(portfolio_entries)]

    seen = {e["ticker"] for e in top}
    for e in portfolio_entries:
        if e["weighted_score"] < MIN_SCORE_THRESHOLD:
            logger.warning(
                "UWAGA: %s w portfolio ma weighted_score %s poniżej progu %s",
                e["ticker"],
                e["weighted_score"],
                MIN_SCORE_THRESHOLD,
            )
        if e["ticker"] not in seen:
            top.append(e)

    top.sort(key=lambda x: x["weighted_score"], reverse=True)
    return top
