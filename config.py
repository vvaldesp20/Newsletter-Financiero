import os
from dotenv import load_dotenv

load_dotenv()

FINVIZ_EMAIL = os.getenv("FINVIZ_EMAIL", "")
FINVIZ_PASSWORD = os.getenv("FINVIZ_PASSWORD", "")

EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = [r.strip() for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r.strip()]
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))

NEWSLETTER_TIME = os.getenv("NEWSLETTER_TIME", "08:30")

# Portfolio holdings — trackable via yfinance
# Fondos privados (Coatue, Polar Capital, Neuberger, FFMM Toesca, etc.) se omiten
PORTFOLIO = {
    "desarrollado": [
        ("VOO",   "Vanguard S&P 500 ETF"),
        ("SPY",   "SPDR S&P 500 ETF"),
        ("IEUR",  "iShares MSCI Europe ETF"),
        ("IEFA",  "iShares MSCI EAFE ETF"),
        ("XLF",   "Financial Select Sector SPDR"),
        ("EWJ",   "iShares MSCI Japan ETF"),
        ("IWO",   "iShares Russell 2000 Growth ETF"),
        ("EWC",   "iShares MSCI Canada ETF"),
        ("AMZN",  "Amazon"),
        ("MSFT",  "Microsoft"),
        ("QQQ",   "Invesco QQQ (Nasdaq 100)"),
        ("XLI",   "Industrial Select Sector SPDR"),
        ("GOOGL", "Alphabet (Google)"),
        ("META",  "Meta Platforms"),
    ],
    "emergente": [
        ("EMXC",  "iShares MSCI EM ex China ETF"),
        ("SPEM",  "SPDR Portfolio Emerging Markets ETF"),
        ("ECH",   "iShares MSCI Chile ETF"),
        ("MCHI",  "iShares MSCI China ETF"),
    ],
    "megatrend": [
        ("SOXX",  "iShares PHLX Semiconductor ETF"),
        ("GRID",  "First Trust NASDAQ Smart Grid ETF"),
        ("COPX",  "Global X Copper Miners ETF"),
        ("SLV",   "iShares Silver ETF"),
        ("NU",    "Nu Holdings"),
        ("IBIT",  "iShares Bitcoin ETF"),
        ("ETHA",  "iShares Ethereum ETF"),
        ("ASML",  "ASML Holding"),
        ("LTMAY", "LATAM Airlines ADR"),
    ],
}

# Flat list of all trackable tickers (for news filtering)
PORTFOLIO_TICKERS = [t for holdings in PORTFOLIO.values() for t, _ in holdings]

# Curated watchlist for stock ideas (analyzed via yfinance, no Finviz needed)
STOCK_WATCHLIST = [
    "NVDA", "AAPL", "JPM", "V",   "LLY",  "AVGO",
    "TSM",  "AMD",  "PLTR","ARM", "MELI", "XOM",
    "BRK-B","BABA", "UBER","COIN","HIMS", "RKLB",
]
