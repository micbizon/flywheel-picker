import json

from shared.config_loader import (
    load_decisions_log,
    load_portfolio,
    load_system_insights,
)
from shared.market_data import get_pnl_pct, get_price_context


def _portfolio_state_section(portfolio: dict, price_ctx: str = "") -> str:
    positions = portfolio.get("positions", [])
    cash_pct = portfolio.get("cash_pct", 0)
    tickers_line = ", ".join(p["ticker"] for p in positions) if positions else "brak"
    lines = [
        f"Aktualne pozycje: {tickers_line}",
        f"Dostępna gotówka: {cash_pct}%",
        "Przy decyzji BUY uwzględnij dostępną gotówkę.",
    ]
    if price_ctx:
        lines.append(price_ctx)
    return "\n".join(lines)


def _position_section(ticker: str, portfolio: dict) -> str:
    positions = portfolio.get("positions", [])
    position = next((p for p in positions if p["ticker"] == ticker), None)
    if position:
        size = position.get("current_weight_pct", 0)
        entry_price = position.get("entry_price", 0)
        position_context = f"POZYCJA W PORTFELU: TAK\nAktualny rozmiar: {size}%"

        pnl_pct = get_pnl_pct(ticker, entry_price)
        if pnl_pct is not None:
            position_context += f"\nP&L od wejścia: {pnl_pct:+.1f}%"
        return position_context
    return "POZYCJA W PORTFELU: NIE\nAktualny rozmiar: brak pozycji"


def _consensus_section(layer4: dict) -> str:
    bull_cs = layer4.get("bull", {}).get("consensus_strength", "N/A")
    bear_cs = layer4.get("bear", {}).get("consensus_strength", "N/A")
    return f"Bull consensus: {bull_cs}\nBear consensus: {bear_cs}"


def build_context(ticker: str, layer2: dict, layer4: dict) -> str:
    price_ctx = get_price_context(ticker)
    decisions_with_feedback = [
        d
        for d in load_decisions_log()
        if d.get("feedback_6m") is not None or d.get("feedback_12m") is not None
    ]
    decisions_with_feedback.sort(key=lambda d: d.get("date", ""), reverse=True)
    recent_feedback = decisions_with_feedback[:10]

    portfolio = load_portfolio()

    sections = [
        (
            "CURRENT PORTFOLIO",
            json.dumps(portfolio, ensure_ascii=False, indent=2),
        ),
        ("STAN PORTFELA", _portfolio_state_section(portfolio, price_ctx)),
        (f"POZYCJA {ticker} W PORTFELU", _position_section(ticker, portfolio)),
        (
            "POPRZEDNIE DECYZJE Z FEEDBACKIEM (od najnowszych, max 10)",
            json.dumps(recent_feedback, ensure_ascii=False, indent=2),
        ),
        (
            "SYSTEM INSIGHTS (agent accuracy & known bias patterns)",
            json.dumps(load_system_insights(), ensure_ascii=False, indent=2),
        ),
        (
            f"LAYER 2 ANALIZA DLA {ticker}",
            json.dumps(layer2, ensure_ascii=False, indent=2),
        ),
        (
            f"LAYER 4 TEZY DLA {ticker} (bull / bear / pre-mortem)",
            json.dumps(layer4, ensure_ascii=False, indent=2),
        ),
        (
            "PEWNOŚĆ ANALIZY",
            _consensus_section(layer4),
        ),
    ]

    return "\n\n".join(f"## {title}\n{content}" for title, content in sections)
