import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://finviz.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _login(email: str, password: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        resp = session.post(
            f"{BASE_URL}/login.ashx",
            data={"email": email, "password": password, "remember": "1"},
            timeout=15,
        )
        if "logout" in resp.text.lower():
            logger.info("Finviz Elite: login successful")
        else:
            logger.warning("Finviz Elite: login may have failed — check credentials")
    except Exception as e:
        logger.error(f"Finviz login error: {e}")
    return session


def get_news(session: requests.Session, count: int = 20) -> list[dict]:
    try:
        resp = session.get(f"{BASE_URL}/news.ashx", timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        news_table = soup.find(id="news-table")
        if not news_table:
            logger.warning("Finviz: news table not found")
            return []

        items = []
        current_date = datetime.now().strftime("%d %b")

        for row in news_table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            date_cell = cells[0].get_text(strip=True)

            # Rows that start with a full date (e.g. "Apr-28-26") are date separators
            if len(date_cell) > 8:
                try:
                    current_date = datetime.strptime(date_cell, "%b-%d-%y").strftime("%d %b")
                except ValueError:
                    current_date = date_cell
                continue

            time_text = date_cell
            news_cell = cells[1]

            link = news_cell.find("a", class_="tab-link") or news_cell.find("a")
            if not link:
                continue

            title = link.get_text(strip=True)
            url   = link.get("href", "")

            # Source is usually a second anchor or a span
            all_links = news_cell.find_all("a")
            source = all_links[-1].get_text(strip=True) if len(all_links) > 1 else ""

            if title:
                items.append({
                    "date":   current_date,
                    "time":   time_text,
                    "title":  title,
                    "url":    url,
                    "source": source,
                })

            if len(items) >= count:
                break

        logger.info(f"Finviz: {len(items)} news items fetched")
        return items

    except Exception as e:
        logger.error(f"Finviz news error: {e}")
        return []


def get_sector_performance(session: requests.Session) -> list[dict]:
    try:
        resp = session.get(
            f"{BASE_URL}/groups.ashx?g=sector&v=120&o=-perf1w",
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")

        sectors = []
        table = soup.find("table", class_="t-home-table") or soup.find("table", attrs={"data-testid": "groups-table"})

        if not table:
            # Fallback: use finvizfinance library (works without Elite auth)
            try:
                from finvizfinance.group.overview import Overview
                import pandas as pd
                ov = Overview()
                df = ov.screener_view(group="Sector")
                for _, row in df.iterrows():
                    chg = str(row.get("Change", "0%")).replace("%", "")
                    try:
                        chg_f = float(chg)
                    except ValueError:
                        chg_f = 0.0
                    sectors.append({
                        "name":    str(row.get("Name", "")),
                        "change":  chg_f,
                        "ytd":     str(row.get("Perf YTD", "-")),
                        "volume":  str(row.get("Volume", "-")),
                    })
                logger.info(f"Sectors via finvizfinance: {len(sectors)}")
                return sectors
            except Exception as e2:
                logger.warning(f"finvizfinance sector fallback error: {e2}")
                return []

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            name = cells[0].get_text(strip=True)
            chg_str = cells[1].get_text(strip=True).replace("%", "")
            try:
                chg_f = float(chg_str)
            except ValueError:
                chg_f = 0.0
            sectors.append({"name": name, "change": chg_f, "ytd": "-", "volume": "-"})

        logger.info(f"Sectors collected: {len(sectors)}")
        return sectors

    except Exception as e:
        logger.error(f"Finviz sector error: {e}")
        return []


def _parse_screener_table(soup: BeautifulSoup, count: int) -> list[dict]:
    table = soup.find("table", id="screener-table") or soup.find("table", class_="screener-table")
    if not table:
        return []
    rows = table.find_all("tr")[1:count + 1]
    items = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        try:
            items.append({
                "ticker":  cells[1].get_text(strip=True),
                "company": cells[2].get_text(strip=True),
                "sector":  cells[3].get_text(strip=True),
                "price":   cells[8].get_text(strip=True),
                "change":  cells[9].get_text(strip=True) if len(cells) > 9 else "-",
                "volume":  cells[10].get_text(strip=True) if len(cells) > 10 else "-",
            })
        except (IndexError, ValueError):
            continue
    return items


def get_top_gainers(session: requests.Session, count: int = 10) -> list[dict]:
    try:
        resp = session.get(
            f"{BASE_URL}/screener.ashx?v=111&s=ta_topgainers&f=sh_price_o5",
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        items = _parse_screener_table(soup, count)
        logger.info(f"Top gainers: {len(items)}")
        return items
    except Exception as e:
        logger.error(f"Finviz gainers error: {e}")
        return []


def get_top_losers(session: requests.Session, count: int = 10) -> list[dict]:
    try:
        resp = session.get(
            f"{BASE_URL}/screener.ashx?v=111&s=ta_toplosers&f=sh_price_o5",
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        items = _parse_screener_table(soup, count)
        logger.info(f"Top losers: {len(items)}")
        return items
    except Exception as e:
        logger.error(f"Finviz losers error: {e}")
        return []


def get_analyst_ratings(session: requests.Session, count: int = 8) -> list[dict]:
    try:
        resp = session.get(f"{BASE_URL}/analyst_ratings_all.ashx", timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table", class_="fullview-ratings-outer")
        if not table:
            return []

        ratings = []
        for row in table.find_all("tr")[1:count + 1]:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            ratings.append({
                "date":    cells[0].get_text(strip=True),
                "action":  cells[1].get_text(strip=True),
                "broker":  cells[2].get_text(strip=True),
                "ticker":  cells[3].get_text(strip=True),
                "rating":  cells[4].get_text(strip=True),
                "target":  cells[5].get_text(strip=True),
            })
        logger.info(f"Analyst ratings: {len(ratings)}")
        return ratings
    except Exception as e:
        logger.error(f"Finviz analyst ratings error: {e}")
        return []


def get_economic_calendar(session: requests.Session, max_events: int = 20) -> list[dict]:
    try:
        resp = session.get(f"{BASE_URL}/calendar.ashx", timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        table = (soup.find("table", id="calendar") or
                 soup.find("table", class_="calendar-table") or
                 soup.find("table", attrs={"data-testid": "calendar-table"}))

        if not table:
            for t in soup.find_all("table"):
                text = t.get_text()
                if any(kw in text for kw in ["High", "Medium", "NFP", "CPI", "GDP"]):
                    table = t
                    break

        if not table:
            logger.warning("Finviz: economic calendar table not found")
            return []

        events = []
        current_date = ""

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue

            if len(cells) == 1 or (len(cells) > 1 and cells[0].get("colspan")):
                text = cells[0].get_text(strip=True)
                if text:
                    current_date = text
                continue

            if len(cells) < 4:
                continue

            time_text    = cells[0].get_text(strip=True)
            country_cell = cells[1]
            country_img  = country_cell.find("img")
            country      = country_img.get("alt", country_cell.get_text(strip=True)) if country_img else country_cell.get_text(strip=True)

            impact_cell  = cells[2]
            impact_img   = impact_cell.find("img")
            impact       = (impact_img.get("alt") or impact_img.get("title") or "") if impact_img else impact_cell.get_text(strip=True)

            event_name   = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            actual       = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            forecast     = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            previous     = cells[6].get_text(strip=True) if len(cells) > 6 else ""

            if event_name:
                events.append({
                    "date":     current_date,
                    "time":     time_text,
                    "country":  country,
                    "impact":   impact,
                    "event":    event_name,
                    "actual":   actual,
                    "forecast": forecast,
                    "previous": previous,
                })

            if len(events) >= max_events:
                break

        logger.info(f"Economic calendar: {len(events)} events fetched")
        return events

    except Exception as e:
        logger.error(f"Finviz calendar error: {e}")
        return []


def collect(email: str, password: str) -> dict:
    session = _login(email, password)
    return {
        "news":            get_news(session, count=20),
        "sectors":         get_sector_performance(session),
        "gainers":         get_top_gainers(session, count=8),
        "losers":          get_top_losers(session, count=8),
        "analyst_ratings": get_analyst_ratings(session, count=8),
        "calendar":        get_economic_calendar(session, max_events=20),
    }
