import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def get_current_price(ticker: str) -> float | None:
    try:
        return yf.Ticker(ticker).fast_info["lastPrice"]
    except Exception as e:
        logger.warning(f"get_current_price({ticker}) failed: {e}")
        return None


def get_pnl_pct(ticker: str, entry_price: float) -> float | None:
    if not entry_price:
        return None
    current_price = get_current_price(ticker)
    if current_price is None:
        return None
    return (current_price - entry_price) / entry_price * 100


def get_price_context(ticker: str) -> str:
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        hist = stock.history(period="30d")

        avg_vol = hist["Volume"].tail(20).mean() if len(hist) >= 20 else None
        today_vol = hist["Volume"].iloc[-1] if len(hist) else None
        vol_ratio = today_vol / avg_vol if avg_vol and today_vol else None

        lines = [
            f"Cena: ${info['lastPrice']:.2f}",
            f"52-tygodniowe minimum: ${info['yearLow']:.2f}",
            f"52-tygodniowe maksimum: ${info['yearHigh']:.2f}",
        ]
        if avg_vol is not None:
            lines.append(f"Średni wolumen 20d: {avg_vol / 1e6:.2f}M akcji")
        if vol_ratio is not None:
            lines.append(f"Wolumen dziś vs średnia: {vol_ratio:.1f}x")

        return (
            "\nAKTUALNE DANE RYNKOWE (pobrane w czasie rzeczywistym):\n" + "\n".join(lines) + "\n"
        )
    except Exception as e:
        logger.warning(f"get_price_context({ticker}) failed: {e}")
        return ""


def get_company_name_context(ticker: str) -> str:
    try:
        i = yf.Ticker(ticker).info
        parts = [f"Ticker: {ticker}"]
        if i.get("longName"):
            parts.append(i["longName"])
        if i.get("sector") or i.get("industry"):
            parts.append(f"{i.get('sector', '?')} / {i.get('industry', '?')}")
        return " — ".join(parts)
    except Exception:
        return f"Ticker: {ticker}"


def get_sentiment_context(ticker: str) -> str:
    try:
        news = yf.Ticker(ticker).news or []
        if not news:
            return f"Ticker: {ticker}\n(brak newsów w yfinance)"
        lines = [f"Ticker: {ticker} — NAJNOWSZE NEWSY:"]
        for item in news[:7]:
            c = item.get("content", {})
            date = c.get("pubDate", "")[:10]
            title = c.get("title", "")
            summary = c.get("summary", "")[:120]
            provider = c.get("provider", {}).get("displayName", "")
            lines.append(f"{date} [{provider}] {title}")
            if summary:
                lines.append(f"  {summary}")
        return "\n".join(lines) + "\n"
    except Exception as e:
        logger.warning(f"get_sentiment_context({ticker}) failed: {e}")
        return f"Ticker: {ticker}\n"


def get_ownership_context(ticker: str) -> str:
    try:
        stock = yf.Ticker(ticker)
        lines = [f"Ticker: {ticker} — DANE WŁASNOŚCIOWE:"]

        major = stock.major_holders
        if major is not None and not major.empty:
            breakdown = major["Value"].to_dict()
            insider_pct = breakdown.get("insidersPercentHeld")
            inst_pct = breakdown.get("institutionsPercentHeld")
            inst_count = breakdown.get("institutionsCount")
            parts = []
            if insider_pct is not None:
                parts.append(f"Insider: {insider_pct * 100:.1f}%")
            if inst_pct is not None:
                count_str = f" ({int(inst_count)} inst.)" if inst_count else ""
                parts.append(f"Instytucje: {inst_pct * 100:.1f}%{count_str}")
            if parts:
                lines.append("  " + " | ".join(parts))

        transactions = stock.insider_transactions
        if transactions is not None and not transactions.empty:
            cutoff = pd.Timestamp.now() - pd.DateOffset(months=3)
            recent = transactions[pd.to_datetime(transactions["Start Date"]) >= cutoff]
            if recent.empty:
                lines.append("  Transakcje insiderów (ostatnie 3 miesiące): brak")
            else:
                lines.append("  Transakcje insiderów (ostatnie 3 miesiące):")
                for _, row in recent.iterrows():
                    date = str(row.get("Start Date", ""))[:10]
                    insider = row.get("Insider", "")
                    position = row.get("Position", "")
                    text = row.get("Text", "")
                    shares = int(row.get("Shares", 0))
                    lines.append(f"  {date} {insider} ({position}): {text[:60]} [{shares:,} akcji]")

        inst = stock.institutional_holders
        if inst is not None and not inst.empty:
            by_change = inst.reindex(inst["pctChange"].abs().sort_values(ascending=False).index)
            lines.append("  Instytucje — największe zmiany:")
            for _, row in by_change.head(5).iterrows():
                holder = row.get("Holder", "")
                value = row.get("Value", 0)
                pct_change = row.get("pctChange", None)
                chg = f" {pct_change * 100:+.1f}%" if pct_change is not None else ""
                lines.append(f"  {holder}: ${value / 1e6:.0f}M{chg}")

        return "\n".join(lines) + "\n"
    except Exception as e:
        logger.warning(f"get_ownership_context({ticker}) failed: {e}")
        return f"Ticker: {ticker}\n"
