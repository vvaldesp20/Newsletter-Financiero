import logging
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)


def _ytd_pct(ticker: str) -> float | None:
    try:
        start = f"{datetime.now().year}-01-01"
        hist = yf.Ticker(ticker).history(start=start)
        if len(hist) < 2:
            return None
        return round(((float(hist["Close"].iloc[-1]) - float(hist["Close"].iloc[0])) / float(hist["Close"].iloc[0])) * 100, 1)
    except Exception:
        return None


def _pros_cons(info: dict, ytd: float | None) -> tuple[list[str], list[str]]:
    pros, cons = [], []

    pe     = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    eps_g  = info.get("earningsGrowth")
    rev_g  = info.get("revenueGrowth")
    margin = info.get("profitMargins")
    d_e    = info.get("debtToEquity")
    div_y  = info.get("dividendYield")
    beta   = info.get("beta")
    target = info.get("targetMeanPrice")
    price  = info.get("currentPrice") or info.get("regularMarketPrice")
    w52h   = info.get("fiftyTwoWeekHigh")
    rec    = info.get("recommendationMean")

    if pe is not None:
        if pe < 15:
            pros.append(f"Valoración atractiva (P/E {pe:.1f}x)")
        elif pe > 40:
            cons.append(f"Valoración exigente (P/E {pe:.1f}x)")

    if fwd_pe is not None and pe is not None and fwd_pe < pe * 0.85:
        pros.append(f"BPA creciente esperado (P/E fwd {fwd_pe:.1f}x)")

    if eps_g is not None:
        if eps_g > 0.15:
            pros.append(f"BPA +{eps_g*100:.0f}% a/a")
        elif eps_g < -0.05:
            cons.append(f"BPA cayendo ({eps_g*100:.0f}% a/a)")

    if rev_g is not None:
        if rev_g > 0.12:
            pros.append(f"Ingresos +{rev_g*100:.0f}% a/a")
        elif rev_g < -0.05:
            cons.append(f"Ingresos en contracción ({rev_g*100:.0f}% a/a)")

    if margin is not None:
        if margin > 0.20:
            pros.append(f"Margen neto {margin*100:.0f}%")
        elif margin < 0:
            cons.append("Pérdidas netas (margen negativo)")

    if d_e is not None:
        if d_e < 30:
            pros.append("Balance sólido (deuda baja)")
        elif d_e > 250:
            cons.append(f"Apalancamiento elevado (D/E {d_e:.0f}%)")

    if div_y is not None and div_y > 0.025:
        pros.append(f"Dividendo {div_y*100:.1f}%")

    if target is not None and price is not None and price > 0:
        upside = (target - price) / price * 100
        if upside > 20:
            pros.append(f"Potencial +{upside:.0f}% (consenso analistas)")
        elif upside < -10:
            cons.append(f"Consenso implica caída ({upside:.0f}%)")

    if w52h is not None and price is not None and w52h > 0:
        from_high = (price - w52h) / w52h * 100
        if from_high < -35:
            pros.append(f"{abs(from_high):.0f}% bajo máximos (posible sobreventa)")
        elif from_high > -3:
            cons.append("Cotiza cerca de máximos anuales")

    if beta is not None and beta > 1.5:
        cons.append(f"Alta volatilidad (beta {beta:.1f})")

    if ytd is not None:
        if ytd < -30:
            pros.append(f"Caída YTD de {ytd:.0f}% puede ser oportunidad")
        elif ytd > 60:
            cons.append(f"+{ytd:.0f}% YTD — valoración puede estar estirada")

    if rec is not None:
        if rec <= 1.8:
            pros.append("Consenso analistas: Compra Fuerte")
        elif rec >= 3.5:
            cons.append("Consenso analistas: Neutral / Venta")

    return pros[:4], cons[:3]


def analyze(tickers: list[str]) -> list[dict]:
    results = []
    for ticker in tickers:
        try:
            t    = yf.Ticker(ticker)
            info = t.info
            if not info:
                continue

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev  = info.get("previousClose")
            chg   = round(((price - prev) / prev) * 100, 2) if price and prev else None
            ytd   = _ytd_pct(ticker)
            pros, cons = _pros_cons(info, ytd)

            results.append({
                "ticker":     ticker,
                "company":    info.get("longName") or info.get("shortName", ticker),
                "sector":     info.get("sector", "-"),
                "price":      f"{price:.2f}" if price else "-",
                "change_pct": chg,
                "ytd":        ytd,
                "pe":         f"{info['trailingPE']:.1f}x"           if info.get("trailingPE")    else "-",
                "fwd_pe":     f"{info['forwardPE']:.1f}x"            if info.get("forwardPE")     else "-",
                "eps_growth": f"{info['earningsGrowth']*100:+.0f}%"  if info.get("earningsGrowth") else "-",
                "rev_growth": f"{info['revenueGrowth']*100:+.0f}%"   if info.get("revenueGrowth") else "-",
                "margin":     f"{info['profitMargins']*100:.1f}%"     if info.get("profitMargins") else "-",
                "div_yield":  f"{info['dividendYield']*100:.1f}%"     if info.get("dividendYield") else "-",
                "target":     f"${info['targetMeanPrice']:.2f}"       if info.get("targetMeanPrice") else "-",
                "beta":       f"{info['beta']:.1f}"                   if info.get("beta")          else "-",
                "pros":       pros,
                "cons":       cons,
            })
            logger.info(f"Analyzed {ticker}: {len(pros)} pros, {len(cons)} cons")
        except Exception as e:
            logger.error(f"stock_analysis [{ticker}]: {e}")
    return results
