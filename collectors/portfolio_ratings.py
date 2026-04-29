import logging
from datetime import datetime, timedelta

import yfinance as yf

import config

logger = logging.getLogger(__name__)

_PRIORITY_TICKERS = ["AMZN", "MSFT", "GOOGL", "META", "SOXX", "NU", "ASML", "MCHI", "ECH"]


def fetch(days: int = 30, max_results: int = 10) -> list[dict]:
    """Fetch recent analyst rating changes for portfolio tickers via yfinance."""
    cutoff = datetime.now() - timedelta(days=days)
    tickers = _PRIORITY_TICKERS + [t for t in config.PORTFOLIO_TICKERS if t not in _PRIORITY_TICKERS]
    ratings = []

    for ticker in tickers:
        if len(ratings) >= max_results:
            break
        try:
            df = yf.Ticker(ticker).upgrades_downgrades
            if df is None or df.empty:
                continue
            df = df.reset_index()
            date_col = "GradeDate" if "GradeDate" in df.columns else df.columns[0]
            df[date_col] = df[date_col].apply(
                lambda d: d.to_pydatetime().replace(tzinfo=None) if hasattr(d, "to_pydatetime") else d
            )
            recent = df[df[date_col] >= cutoff].head(3)
            for _, row in recent.iterrows():
                action = str(row.get("Action", "")).strip()
                if action.lower() in ("", "main", "reit"):
                    continue
                to_grade   = str(row.get("ToGrade",   "-")).strip()
                from_grade = str(row.get("FromGrade", "-")).strip()
                firm       = str(row.get("Firm",      "-")).strip()
                date_val   = row[date_col]
                date_str   = date_val.strftime("%d %b") if hasattr(date_val, "strftime") else str(date_val)[:10]

                ratings.append({
                    "date":   date_str,
                    "action": action,
                    "broker": firm,
                    "ticker": ticker,
                    "rating": f"{from_grade} → {to_grade}" if from_grade and from_grade != "-" else to_grade,
                    "target": "-",
                })
        except Exception as e:
            logger.debug(f"ratings [{ticker}]: {e}")

    logger.info(f"yfinance analyst ratings: {len(ratings)} items")
    return ratings[:max_results]
