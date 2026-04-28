import logging
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)


FRED_SERIES = {
    "fed_rate":         "DFEDTARU",
    "cpi":              "CPIAUCSL",
    "core_cpi":         "CPILFESL",
    "pce":              "PCEPI",
    "core_pce":         "PCEPILFE",
    "unemployment":     "UNRATE",
    "gdp":              "GDPC1",
    "industrial_prod":  "INDPRO",
    "consumer_sent":    "UMCSENT",
    "yield_2y":         "DGS2",
    "yield_5y":         "DGS5",
    "yield_10y":        "DGS10",
    "yield_30y":        "DGS30",
    "yield_curve":      "T10Y2Y",
    "hy_spread":        "BAMLH0A0HYM2",
    "ig_spread":        "BAMLC0A0CM",
    "vix":              "VIXCLS",
}


def _yoy(series: pd.Series) -> float | None:
    series = series.dropna()
    if len(series) < 13:
        return None
    return round(((series.iloc[-1] - series.iloc[-13]) / series.iloc[-13]) * 100, 2)


def _mom(series: pd.Series) -> float | None:
    series = series.dropna()
    if len(series) < 2:
        return None
    return round(((series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]) * 100, 2)


def _qoq_annualized(series: pd.Series) -> float | None:
    series = series.dropna()
    if len(series) < 2:
        return None
    return round(((series.iloc[-1] - series.iloc[-2]) / series.iloc[-2]) * 400, 2)


def _latest(series: pd.Series, decimals: int = 2):
    series = series.dropna()
    if series.empty:
        return None, None
    return round(series.iloc[-1], decimals), series.index[-1].strftime("%b %Y")


def collect(fred_api_key: str) -> dict:
    try:
        from fredapi import Fred
        fred = Fred(api_key=fred_api_key)
    except Exception as e:
        logger.error(f"FRED init error: {e}")
        return {}

    data = {}

    def fetch(key: str, obs_start: str = "2020-01-01") -> pd.Series | None:
        try:
            return fred.get_series(FRED_SERIES[key], observation_start=obs_start)
        except Exception as e:
            logger.warning(f"FRED fetch error [{key}]: {e}")
            return None

    # Fed Funds Rate
    s = fetch("fed_rate")
    if s is not None:
        val, date = _latest(s)
        data["fed_rate"] = {"value": f"{val}%", "change": None, "date": date, "label": "Fed Funds Rate (techo)"}

    # CPI YoY
    s = fetch("cpi")
    if s is not None:
        val, date = _latest(s)
        yoy = _yoy(s)
        data["cpi"] = {"value": f"{yoy}% a/a", "change": _mom(s), "date": date, "label": "IPC EE.UU. (YoY)"}

    # Core CPI YoY
    s = fetch("core_cpi")
    if s is not None:
        val, date = _latest(s)
        yoy = _yoy(s)
        data["core_cpi"] = {"value": f"{yoy}% a/a", "change": _mom(s), "date": date, "label": "IPC Subyacente EE.UU. (YoY)"}

    # Core PCE YoY (Fed preferred)
    s = fetch("core_pce")
    if s is not None:
        yoy = _yoy(s)
        _, date = _latest(s)
        data["core_pce"] = {"value": f"{yoy}% a/a", "change": None, "date": date, "label": "PCE Subyacente (objetivo Fed)"}

    # Unemployment
    s = fetch("unemployment")
    if s is not None:
        val, date = _latest(s)
        data["unemployment"] = {"value": f"{val}%", "change": _mom(s), "date": date, "label": "Tasa de Desempleo EE.UU."}

    # Real GDP QoQ annualized
    s = fetch("gdp", obs_start="2018-01-01")
    if s is not None:
        growth = _qoq_annualized(s)
        _, date = _latest(s)
        data["gdp"] = {"value": f"{growth}% (anualizado)", "change": None, "date": date, "label": "PIB Real EE.UU. (QoQ anualizado)"}

    # Treasury yields
    for key, label in [
        ("yield_2y",  "Treasury 2 años"),
        ("yield_5y",  "Treasury 5 años"),
        ("yield_10y", "Treasury 10 años"),
        ("yield_30y", "Treasury 30 años"),
    ]:
        s = fetch(key)
        if s is not None:
            val, date = _latest(s)
            s_clean = s.dropna()
            prev = round(s_clean.iloc[-2], 2) if len(s_clean) >= 2 else None
            bps_chg = round((val - prev) * 100, 1) if prev is not None else None
            chg_str = f"{bps_chg:+.0f} bps" if bps_chg is not None else "-"
            data[key] = {
                "value": f"{val}%",
                "change": chg_str,
                "change_positive": bps_chg is not None and bps_chg <= 0,
                "date": date,
                "label": label,
            }

    # Yield curve (10Y-2Y)
    s = fetch("yield_curve")
    if s is not None:
        val, date = _latest(s)
        data["yield_curve"] = {
            "value": f"{val:+.0f} bps",
            "change": None,
            "change_positive": val is not None and val >= 0,
            "date": date,
            "label": "Curva 10Y-2Y (spread)",
        }

    # Credit spreads
    for key, label in [
        ("hy_spread", "Spread High Yield (OAS)"),
        ("ig_spread", "Spread Investment Grade (OAS)"),
    ]:
        s = fetch(key)
        if s is not None:
            val, date = _latest(s)
            s_clean = s.dropna()
            prev = round(s_clean.iloc[-2], 2) if len(s_clean) >= 2 else None
            bps_chg = round((val - prev) * 100, 1) if prev is not None else None
            chg_str = f"{bps_chg:+.0f} bps" if bps_chg is not None else "-"
            data[key] = {
                "value": f"{val:.0f} bps",
                "change": chg_str,
                "change_positive": bps_chg is not None and bps_chg <= 0,
                "date": date,
                "label": label,
            }

    # VIX
    s = fetch("vix")
    if s is not None:
        val, date = _latest(s)
        s_clean = s.dropna()
        prev = s_clean.iloc[-2] if len(s_clean) >= 2 else None
        chg = round(val - prev, 2) if prev else None
        data["vix"] = {
            "value": f"{val:.1f}",
            "change": f"{chg:+.2f}" if chg else "-",
            "change_positive": chg is not None and chg <= 0,
            "date": date,
            "label": "VIX (volatilidad implícita S&P500)",
        }

    logger.info(f"Macro data collected: {list(data.keys())}")
    return data
