import logging

import yfinance as yf

logger = logging.getLogger(__name__)

FILTERS = {
    "market_cap_min": 1_000_000_000,
    "market_cap_max": 100_000_000_000,
    "revenue_growth_yoy_min": 0.10,
    "gross_margin_min": 0.35,
    "current_ratio_min": 1.2,
    "net_debt_to_revenue_max": 3.0,
    "ev_to_revenue_max": 20.0,
    "ev_to_revenue_min": 0.5,
    "insider_ownership_min": 0.03,
}


def _get_metrics(ticker: str) -> dict:
    info = yf.Ticker(ticker).info

    total_debt = info.get("totalDebt")
    total_cash = info.get("totalCash")
    total_revenue = info.get("totalRevenue")

    net_debt_to_revenue = None
    if total_debt is not None and total_cash is not None and total_revenue:
        net_debt_to_revenue = (total_debt - total_cash) / total_revenue

    return {
        "market_cap": info.get("marketCap"),
        "revenue_growth_yoy": info.get("revenueGrowth"),
        "gross_margin": info.get("grossMargins"),
        "current_ratio": info.get("currentRatio"),
        "net_debt_to_revenue": net_debt_to_revenue,
        "ev_to_revenue": info.get("enterpriseToRevenue"),
        "insider_ownership": info.get("heldPercentInsiders"),
    }


def _check(value, op, threshold) -> bool:
    if value is None:
        return True
    if op == ">=":
        return value >= threshold
    if op == "<=":
        return value <= threshold
    return True


def _failed_filters(metrics: dict) -> list[str]:
    checks = [
        ("market_cap", metrics["market_cap"], ">=", FILTERS["market_cap_min"]),
        ("market_cap", metrics["market_cap"], "<=", FILTERS["market_cap_max"]),
        (
            "revenue_growth_yoy",
            metrics["revenue_growth_yoy"],
            ">=",
            FILTERS["revenue_growth_yoy_min"],
        ),
        ("gross_margin", metrics["gross_margin"], ">=", FILTERS["gross_margin_min"]),
        ("current_ratio", metrics["current_ratio"], ">=", FILTERS["current_ratio_min"]),
        (
            "net_debt_to_revenue",
            metrics["net_debt_to_revenue"],
            "<=",
            FILTERS["net_debt_to_revenue_max"],
        ),
        ("ev_to_revenue", metrics["ev_to_revenue"], "<=", FILTERS["ev_to_revenue_max"]),
        ("ev_to_revenue", metrics["ev_to_revenue"], ">=", FILTERS["ev_to_revenue_min"]),
        (
            "insider_ownership",
            metrics["insider_ownership"],
            ">=",
            FILTERS["insider_ownership_min"],
        ),
    ]
    return [
        name
        for name, value, op, threshold in checks
        if not _check(value, op, threshold)
    ]


def apply_prefilter(tickers: list[str]) -> tuple[list[str], list[str]]:
    passing, rejected = [], []
    for ticker in tickers:
        try:
            metrics = _get_metrics(ticker)
            failed = _failed_filters(metrics)
            if failed:
                logger.info(f"[prefilter] {ticker}: REJECT — {failed}")
                rejected.append(ticker)
            else:
                logger.info(f"[prefilter] {ticker}: PASS")
                passing.append(ticker)
        except Exception as e:
            logger.warning(f"[prefilter] {ticker}: błąd danych, przepuszczam ({e})")
            passing.append(ticker)
    logger.info(f"[prefilter] {len(passing)}/{len(tickers)} tickerów przeszło filtr")
    return passing, rejected
