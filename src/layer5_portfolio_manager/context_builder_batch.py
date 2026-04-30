import json
from typing import Any

from shared.config_loader import load_decisions_log, load_system_insights


def _portfolio_section(portfolio: dict) -> str:
    positions = portfolio.get("positions", [])
    cash_pct = portfolio.get("cash_pct", 0)
    tickers = ", ".join(p["ticker"] for p in positions) if positions else "brak"
    return (
        f"Aktualne pozycje: {tickers}\n"
        f"Dostępna gotówka: {cash_pct}%\n"
        "Suma target_position_size_pct dla BUY i ADD nie może przekroczyć dostępnej gotówki."
    )


def _decisions_feedback_section() -> str:
    decisions = [
        d
        for d in load_decisions_log()
        if d.get("feedback_6m") is not None or d.get("feedback_12m") is not None
    ]
    decisions.sort(key=lambda d: d.get("date", ""), reverse=True)
    return json.dumps(decisions[:10], ensure_ascii=False, indent=2)


def _format_ticker_context(c: dict) -> str:
    l2 = c.get("l2", {})
    l4 = c.get("l4", {})
    bull = l4.get("bull", {})
    bear = l4.get("bear", {})
    premortem = l4.get("premortem", {})

    fundamental = l2.get("fundamental", {})
    technical = l2.get("technical", {})

    position_line = f"Pozycja: {'TAK' if c['in_portfolio'] else 'NIE'}"
    if c["in_portfolio"]:
        position_line += f" | rozmiar: {c['current_size']}%"
        if c.get("pnl_pct") is not None:
            position_line += f" | P&L: {c['pnl_pct']:+.1f}%"

    lines = [
        f"### {c['ticker']}",
        position_line,
        "",
        "FUNDAMENTAL:",
        f"  flywheel: {fundamental.get('summary', 'BRAK')}",
        f"  strengths: {', '.join(fundamental.get('key_strengths', []))}",
        f"  risks: {', '.join(fundamental.get('key_risks', []))}",
        "",
        "TECHNICZNY:",
        f"  {technical.get('summary', 'BRAK')}",
        f"  entry: {technical.get('entry_zone', '')} | stop: {technical.get('invalidation_level', '')}",
        "",
        "BULL CASE:",
        f"  teza: {bull.get('core_thesis', 'BRAK')}",
        f"  flywheel: {bull.get('flywheel_mechanism', '')}",
        f"  upside: {bull.get('upside_x', '?')}x | target: ${bull.get('price_target_3yr', '?')}",
        f"  założenia: {'; '.join(bull.get('key_assumptions', []))}",
        "",
        "BEAR CASE:",
        f"  teza: {bear.get('central_thesis', 'BRAK')}",
        f"  top ryzyko: {bear.get('top_risk', '')}",
        f"  stress: {bear.get('stress_test', '')}",
        f"  co zmieni zdanie: {bear.get('what_would_change_mind', '')}",
        "",
        "PRE-MORTEM (top scenariusze):",
    ]

    scenarios = premortem.get("failure_scenarios", [])[:2]
    for s in scenarios:
        lines.append(
            f"  [{s.get('probability', '?')}] {s.get('description', '')} "
            f"— sygnał: {s.get('earliest_warning_signal', '')}"
        )

    lines.append("")
    return "\n".join(lines)


def _format_allocator_ticker(phase1: dict, candidate: dict) -> str:
    l4 = candidate.get("l4", {})
    l2 = candidate.get("l2", {})
    bull = l4.get("bull", {})
    technical = l2.get("technical", {})

    lines = [f"### {phase1['ticker']}"]
    if candidate.get("in_portfolio"):
        lines.append(f"  W portfelu: {candidate['current_size']}%")
        if candidate.get("pnl_pct") is not None:
            lines.append(f"  P&L: {candidate['pnl_pct']:+.1f}%")
        lines.append(f"  Wstępna decyzja: {phase1.get('preliminary_action', '?')}")
    lines.append(f"  Ocena: {phase1.get('note', '')}")
    lines.append(
        f"  Bull: {bull.get('upside_x', '?')}x | target: ${bull.get('price_target_3yr', '?')} | {bull.get('core_thesis', '')}"
    )
    lines.append(
        f"  Techniczny: entry={technical.get('entry_zone', '?')} | stop={technical.get('invalidation_level', '?')}"
    )
    return "\n".join(lines)


def build_allocator_context(
    phase1_results: list[dict],
    candidates: list[dict],
    portfolio: dict,
) -> str:
    by_ticker: dict[str, Any] = {c["ticker"]: c for c in candidates}

    portfolio_entries = [
        r for r in phase1_results if by_ticker.get(r["ticker"], {}).get("in_portfolio")
    ]
    buy_candidates = [
        r for r in phase1_results if not by_ticker.get(r["ticker"], {}).get("in_portfolio")
    ]

    def fmt(r: dict) -> str:
        return _format_allocator_ticker(r, by_ticker.get(r["ticker"], {}))

    sections = [
        ("STAN PORTFELA", _portfolio_section(portfolio)),
        (
            "POPRZEDNIE DECYZJE Z FEEDBACKIEM (od najnowszych, max 10)",
            _decisions_feedback_section(),
        ),
        (
            "SYSTEM INSIGHTS (agent accuracy & known bias patterns)",
            json.dumps(load_system_insights(), ensure_ascii=False, indent=2),
        ),
        ("POZYCJE W PORTFELU", "\n\n".join(fmt(r) for r in portfolio_entries) or "brak"),
        (
            f"KANDYDACI BUY ({len(buy_candidates)})",
            "\n\n".join(fmt(r) for r in buy_candidates) or "brak",
        ),
    ]
    return "\n\n".join(f"## {title}\n{content}" for title, content in sections)


def build_batch_context(candidates: list[dict], portfolio: dict) -> str:
    sections = [
        (
            "CURRENT PORTFOLIO",
            json.dumps(portfolio, ensure_ascii=False, indent=2),
        ),
        ("STAN PORTFELA", _portfolio_section(portfolio)),
        (
            "POPRZEDNIE DECYZJE Z FEEDBACKIEM (od najnowszych, max 10)",
            _decisions_feedback_section(),
        ),
        (
            "SYSTEM INSIGHTS (agent accuracy & known bias patterns)",
            json.dumps(load_system_insights(), ensure_ascii=False, indent=2),
        ),
        (
            f"KANDYDACI DO OCENY ({len(candidates)})",
            "\n\n".join(_format_ticker_context(c) for c in candidates),
        ),
    ]
    return "\n\n".join(f"## {title}\n{content}" for title, content in sections)
