import logging

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
            "\nAKTUALNE DANE RYNKOWE (pobrane w czasie rzeczywistym):\n"
            + "\n".join(lines)
            + "\n"
        )
    except Exception as e:
        logger.warning(f"get_price_context({ticker}) failed: {e}")
        return ""


def get_financial_context(ticker: str) -> str:
    try:
        stock = yf.Ticker(ticker)
        i = stock.info
        rev = i.get("totalRevenue")
        rev_growth = i.get("revenueGrowth")
        gm = i.get("grossMargins")
        fcf = i.get("freeCashflow")
        insider = i.get("heldPercentInsiders")
        ev_rev = i.get("enterpriseToRevenue")
        cash = i.get("totalCash")
        debt = i.get("totalDebt")

        lines = []
        if rev:
            lines.append(f"Revenue TTM: ${rev / 1e6:.0f}M")
        if rev_growth is not None:
            lines.append(f"Revenue Growth YoY: {rev_growth * 100:+.1f}%")
        if gm is not None:
            lines.append(f"Gross Margin: {gm * 100:.1f}%")
        if fcf is not None:
            lines.append(f"FCF TTM: ${fcf / 1e6:+.0f}M")
        if cash is not None and debt is not None:
            net_cash = (cash - debt) / 1e6
            lines.append(f"Dług netto: ${net_cash:+.0f}M")
        if insider is not None:
            lines.append(f"Insider Ownership: {insider * 100:.1f}%")
        if ev_rev is not None:
            lines.append(f"EV/Revenue: {ev_rev:.1f}x")

        if not lines:
            return ""
        return (
            "\nAKTUALNE DANE FINANSOWE (pobrane w czasie rzeczywistym):\n"
            + "\n".join(lines)
            + "\n"
        )
    except Exception:
        logger.warning(f"get_financial_context({ticker}) failed — brak danych")
        return ""
